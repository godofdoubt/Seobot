
# analyzer/generate_ai_recommendations.py
import json
import logging
from typing import Callable, Coroutine, Any, Tuple, Optional

# Assuming LLMAnalysisPrompts is in the same directory or a known path
# For a typical structure where llm_analysis_process.py and this file are in 'analyzer'
from .generate_ai_recommendations_prompt import build_ai_recommendations_prompt

async def generate_ai_recommendations_content(
    llm_analysis_all: dict,
    logger: logging.Logger,
    call_gemini_api_func: Callable[[str], Coroutine[Any, Any, str]],
    call_mistral_api_func: Callable[[str, str], Coroutine[Any, Any, Tuple[Optional[str], Optional[str]]]],
    gemini_model_available: bool,
    mistral_configured: bool
) -> str:
    """
    Generates AI-powered strategic insights and recommendations based on aggregated LLM analysis.
    """
    if not gemini_model_available and not mistral_configured:
        logger.error("Neither Gemini nor Mistral is configured. Cannot generate AI recommendations.")
        return "AI recommendations could not be generated due to model initialization/configuration issues."

    main_page_analysis = llm_analysis_all.get('main_page', {})
    technical_stats = llm_analysis_all.get('technical_statistics', {})
    other_pages = {url: data for url, data in llm_analysis_all.items()
                    if url not in ['main_page', 'technical_statistics'] and data}

    all_keywords = []
    all_seo_keywords = []
    all_topic_categories = []
    all_target_audiences = []
    all_tones = []
    all_summaries = []

    if main_page_analysis and not main_page_analysis.get('error'):
        all_keywords.extend(k for k in main_page_analysis.get('keywords', []) if k)
        all_seo_keywords.extend(sk for sk in main_page_analysis.get('suggested_keywords_for_seo', []) if sk)
        all_topic_categories.extend(tc for tc in main_page_analysis.get('topic_categories', []) if tc)
        all_target_audiences.extend(ta for ta in main_page_analysis.get('target_audience', []) if ta)
        if main_page_analysis.get('overall_tone'):
            all_tones.append(main_page_analysis.get('overall_tone'))
        if main_page_analysis.get('content_summary'):
            all_summaries.append(f"Main Page ({main_page_analysis.get('url', 'N/A')}): {main_page_analysis.get('content_summary')}")

    for page_url, page_data in other_pages.items():
        if page_data and not page_data.get('error'):
            all_keywords.extend(k for k in page_data.get('keywords', []) if k)
            all_seo_keywords.extend(sk for sk in page_data.get('suggested_keywords_for_seo', []) if sk)
            all_topic_categories.extend(tc for tc in page_data.get('topic_categories', []) if tc)
            all_target_audiences.extend(ta for ta in page_data.get('target_audience', []) if ta)
            if page_data.get('overall_tone'):
                all_tones.append(page_data.get('overall_tone'))
            if page_data.get('content_summary'):
                all_summaries.append(f"{page_url}: {page_data.get('content_summary')}")

    website_data_summary = {
        "total_pages_analyzed": len([p for p_url, p in llm_analysis_all.items()
                                    if p and not p.get('error') and p_url not in ['technical_statistics']]),
        "main_page_url": main_page_analysis.get('url', 'Unknown'),
        "all_keywords": list(set(all_keywords)),
        "all_seo_keywords": list(set(all_seo_keywords)),
        "all_topic_categories": list(set(all_topic_categories)),
        "all_target_audiences": list(set(all_target_audiences)),
        "all_content_tones": list(set(all_tones)),
        "content_summaries_sample": all_summaries[:15],
        "main_page_header_elements": main_page_analysis.get('header', []),
        "main_page_footer_elements": main_page_analysis.get('footer', []),
        "technical_statistics": technical_stats
    }

    # Use the imported build_ai_recommendations_prompt function
    prompt = build_ai_recommendations_prompt(website_data_summary)

    ai_response_str = None
    llm_provider_recs = "N/A"
    error_message_for_recs = "AI recommendations failed for both primary and fallback LLMs."
    main_page_url_for_log = website_data_summary['main_page_url']


    try:
        if gemini_model_available:
            logger.info(f"Generating AI-powered recommendations (Gemini attempt) for main URL: {main_page_url_for_log}")
            ai_response_str = await call_gemini_api_func(prompt)
            llm_provider_recs = "Gemini"

        if not ai_response_str:
            if gemini_model_available:
                logger.warning("Gemini returned empty response for AI recommendations. Attempting Mistral fallback.")
            else:
                logger.info("Gemini not available. Attempting AI recommendations with Mistral.")

            if mistral_configured:
                mistral_response, mistral_error = await call_mistral_api_func(prompt, "ai_recommendations_fallback")
                if mistral_error:
                    logger.error(f"Mistral fallback for AI recommendations also failed: {mistral_error}")
                    error_message_for_recs = f"Primary LLM (Gemini) failed/not configured; Mistral fallback for recommendations failed: {mistral_error}"
                elif mistral_response:
                    ai_response_str = mistral_response
                    llm_provider_recs = "Mistral (fallback)"
                    logger.info("Successfully used Mistral as fallback for AI recommendations.")
                else:
                    logger.error("Mistral fallback for AI recommendations returned empty response without explicit error.")
                    error_message_for_recs = "Primary LLM (Gemini) failed/not configured; Mistral fallback for recommendations returned empty."
            else:
                logger.warning("Primary LLM failed/not configured for recommendations, and Mistral is not configured.")
                error_message_for_recs = "Primary LLM (Gemini) failed/not configured for recommendations; Mistral fallback not configured."

        if not ai_response_str:
            logger.error(f"All LLM attempts for AI recommendations failed. Final error state: {error_message_for_recs}")
            return f"AI recommendations could not be generated. {error_message_for_recs}"

        try:
            cleaned_response = ai_response_str.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            recommendations_data = json.loads(cleaned_response)

            formatted_recommendations = []

            strategic_recs = recommendations_data.get('strategic_recommendations', [])
            if strategic_recs:
                formatted_recommendations.append("### Strategic Recommendations")
                for i, rec in enumerate(strategic_recs, 1):
                    category = rec.get('category', 'General')
                    title = rec.get('title', 'Recommendation')
                    description = rec.get('description', '')
                    priority = rec.get('priority', 'Medium')
                    difficulty = rec.get('implementation_difficulty', 'Medium')
                    based_on_data = rec.get('based_on_data', '')

                    formatted_recommendations.append(f"#### {i}. {title} ({category})")
                    formatted_recommendations.append(f"**Priority**: {priority} | **Implementation**: {difficulty}")
                    if based_on_data:
                        formatted_recommendations.append(f"**Data Source**: {based_on_data}")
                    formatted_recommendations.append(description)
                    formatted_recommendations.append("")

            seo_recs = recommendations_data.get('seo_content_optimization', [])
            if seo_recs: # This key is 'seo_optimization_insights' in the prompt, changed for consistency
                formatted_recommendations.append("### SEO Optimization Insights") # Changed title for consistency
                for rec in seo_recs:
                    focus_area = rec.get('focus_area', 'SEO Suggestion')
                    # Map new prompt structure to old formatting variables
                    current_issue = rec.get('observed_issue_or_opportunity', '') 
                    recommendation = rec.get('insight_derived', '') # This is more of an insight now
                    expected_impact = rec.get('potential_impact_if_addressed', '')
                    pages_affected_str = ""
                    if rec.get('example_strategic_action'): # Adding strategic action
                        recommendation += f"\n**Strategic Action Example**: {rec.get('example_strategic_action')}"
                    if rec.get('supporting_data_points'): # Adding supporting data
                         recommendation += f"\n**Supporting Data**: {', '.join(rec.get('supporting_data_points'))}"


                    formatted_recommendations.append(f"#### {focus_area}")
                    if current_issue:
                        formatted_recommendations.append(f"**Observed Issue/Opportunity**: {current_issue}")
                    formatted_recommendations.append(f"**Insight & Action**: {recommendation}")
                    if expected_impact:
                        formatted_recommendations.append(f"**Potential Impact**: {expected_impact}")
                    # 'pages_affected' is not directly in the new prompt structure for seo_optimization_insights
                    # We can leave it out or infer if possible, for now, leaving out.
                    formatted_recommendations.append("")
            
            # Handle Target Audience Personas (New Section)
            personas = recommendations_data.get('target_audience_personas', [])
            if personas:
                formatted_recommendations.append("### Target Audience Personas")
                for i, persona in enumerate(personas, 1):
                    formatted_recommendations.append(f"#### Persona {i}: {persona.get('persona_name', 'N/A')}")
                    if persona.get('demographics'):
                        formatted_recommendations.append(f"**Demographics**: {persona.get('demographics')}")
                    if persona.get('occupation_role'):
                        formatted_recommendations.append(f"**Occupation/Role**: {persona.get('occupation_role')}")
                    if persona.get('goals_related_to_site'):
                        formatted_recommendations.append(f"**Goals (related to site)**: {'; '.join(persona.get('goals_related_to_site'))}")
                    if persona.get('pain_points_challenges'):
                        formatted_recommendations.append(f"**Pain Points/Challenges**: {'; '.join(persona.get('pain_points_challenges'))}")
                    if persona.get('motivations_for_using_site'):
                        formatted_recommendations.append(f"**Motivations for Using Site**: {'; '.join(persona.get('motivations_for_using_site'))}")
                    if persona.get('information_sources'):
                        formatted_recommendations.append(f"**Information Sources**: {'; '.join(persona.get('information_sources'))}")
                    if persona.get('key_message_for_persona'):
                         formatted_recommendations.append(f"**Key Message**: {persona.get('key_message_for_persona')}")
                    formatted_recommendations.append("")


            content_insights = recommendations_data.get('content_strategy_insights', [])
            if content_insights:
                formatted_recommendations.append("### Content Strategy Insights")
                for i, insight_data in enumerate(content_insights, 1):
                    insight = insight_data.get('insight_statement', '') # Mapped from new prompt
                    supporting_data = insight_data.get('supporting_data', '')
                    implications = insight_data.get('implications_for_content', '') # New field

                    formatted_recommendations.append(f"#### Insight {i}: {insight}")
                    if supporting_data:
                        formatted_recommendations.append(f"**Supporting Data**: {supporting_data}")
                    if implications:
                        formatted_recommendations.append(f"**Implications for Content**: {implications}")

                    illustrative_opp = insight_data.get('illustrative_content_opportunity')
                    if illustrative_opp:
                        formatted_recommendations.append("**Illustrative Content Opportunity:**")
                        formatted_recommendations.append(f"- **Type**: {illustrative_opp.get('opportunity_type', 'N/A')}")
                        formatted_recommendations.append(f"  - **Description**: {illustrative_opp.get('description', '')}")
                        formatted_recommendations.append(f"  - **Target Persona Alignment**: {illustrative_opp.get('target_persona_alignment', '')}")
                        if illustrative_opp.get('potential_topics_or_angles'):
                            topics = "; ".join(illustrative_opp.get('potential_topics_or_angles', []))
                            formatted_recommendations.append(f"  - **Potential Topics/Angles**: {topics}")
                        formatted_recommendations.append(f"  - **Justification**: {illustrative_opp.get('justification_based_on_data', '')}")
                    formatted_recommendations.append("")

            # The old 'article_content_tasks' and 'product_content_tasks' are not directly generated
            # by the new prompt structure which focuses more on strategic insights and illustrative examples.
            # We will remove these sections from formatting or adapt if similar data is present.
            # For now, removing them as the new prompt doesn't produce this granular task list.

            if not formatted_recommendations:
                logger.warning(f"AI ({llm_provider_recs}) generated data for recommendations, but no specific sections were populated based on the new prompt structure.")
                return f"AI ({llm_provider_recs}) generated data, but it was not in the expected format or was empty after processing the new structure."

            logger.info(f"Successfully generated and formatted AI-powered recommendations using {llm_provider_recs}.")
            return "\n".join(formatted_recommendations)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI recommendations JSON from {llm_provider_recs}: {e}. Raw response: '{ai_response_str[:500]}'")
            return f"AI recommendations were generated by {llm_provider_recs} but could not be parsed properly. Raw response (first 500 chars): {ai_response_str[:500]}..."

    except Exception as e:
        logger.error(f"Error generating AI recommendations: {e}", exc_info=True)
        return f"An error occurred while generating AI recommendations: {str(e)}"
