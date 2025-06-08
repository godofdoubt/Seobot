# analyzer/llm_report/generate_ai_recommendations.py
import json
import logging
from typing import Callable, Coroutine, Any, Tuple, Optional

# Assuming LLMAnalysisPrompts is in the same directory or a known path
# For a typical structure where llm_analysis_process.py and this file are in 'analyzer'
from .generate_ai_recommendations_prompt import build_ai_recommendations_prompt
# Import language_manager
# Assuming 'Seobot' is a package accessible in PYTHONPATH,
# or utils is a sibling package to analyzer under a common root.
# If analyzer and Seobot.utils are from different top-level structures, ensure PYTHONPATH is correct.
# A common structure might be project_root/analyzer and project_root/Seobot/utils.
# For this solution, we'll assume `from Seobot.utils.language_support import language_manager` is viable.
# If `utils` is a direct sibling of `analyzer` (e.g. project_root/analyzer, project_root/utils),
# then `from ..utils.language_support import language_manager` would be used.
try:
    from utils.language_support import language_manager
except ImportError:
    # Fallback for environments where Seobot might not be directly in PYTHONPATH
    # or for local testing scenarios. This assumes utils is a sibling of analyzer.
    try:
        from ..utils.language_support import language_manager
    except ImportError:
        # As a last resort, if language_manager cannot be imported,
        # create a dummy one that returns the key, to prevent crashes,
        # though translations will not work.
        logging.error("Critical: language_manager could not be imported. Translations will not be applied for dynamic labels.")
        class DummyLanguageManager:
            def get_text(self, key, lang="en", *args, fallback=None, **kwargs):
                return fallback if fallback is not None else key
        language_manager = DummyLanguageManager()


async def generate_ai_recommendations_content(
    llm_analysis_all: dict,
    logger: logging.Logger,
    call_gemini_api_func: Callable[[str], Coroutine[Any, Any, str]],
    call_mistral_api_func: Callable[[str, str], Coroutine[Any, Any, Tuple[Optional[str], Optional[str]]]],
    gemini_model_available: bool,
    mistral_configured: bool,
    language_code: str = "en"  # Added language_code parameter back
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

    prompt = build_ai_recommendations_prompt(website_data_summary, language_code=language_code) # Pass language_code

    # Section titles - using language_manager for consistency
    title_strategic_recommendations = language_manager.get_text("rec_title_strategic", language_code, fallback="### Strategic Recommendations")
    title_seo_optimization_insights = language_manager.get_text("rec_title_seo", language_code, fallback="### SEO Optimization Insights")
    title_target_audience_personas = language_manager.get_text("rec_title_personas", language_code, fallback="### Target Audience Personas")
    title_content_strategy_insights = language_manager.get_text("rec_title_content_insights", language_code, fallback="### Content Strategy Insights")

    ai_response_str = None
    llm_provider_recs = "N/A"
    error_message_for_recs = "AI recommendations failed for both primary and fallback LLMs."
    main_page_url_for_log = website_data_summary['main_page_url']

    try:
        if gemini_model_available:
            logger.info(f"Generating AI-powered recommendations (Gemini attempt) for main URL: {main_page_url_for_log}, Lang: {language_code}")
            ai_response_str = await call_gemini_api_func(prompt)
            llm_provider_recs = "Gemini"

        if not ai_response_str:
            if gemini_model_available:
                logger.warning(f"Gemini returned empty response for AI recommendations (Lang: {language_code}). Attempting Mistral fallback.")
            else:
                logger.info(f"Gemini not available. Attempting AI recommendations with Mistral (Lang: {language_code}).")

            if mistral_configured:
                mistral_response, mistral_error = await call_mistral_api_func(prompt, "ai_recommendations_fallback")
                if mistral_error:
                    # FIX: Enhanced logging for timeout-prone calls. The provided traceback showed a ReadTimeout,
                    # which is common for long-running analyses. This log now provides better diagnostic guidance.
                    logger.error(
                        f"Mistral fallback for AI recommendations also failed (Lang: {language_code}): {mistral_error}. "
                        "This is a long-running analysis; a frequent cause is an API timeout. "
                        "Verify the HTTP client timeout configuration in the underlying API call function."
                    )
                    error_message_for_recs = (
                        f"Primary LLM (Gemini) failed/not configured; "
                        f"Mistral fallback for recommendations failed: {mistral_error} "
                        "(This may be due to a service timeout)."
                    )
                elif mistral_response:
                    ai_response_str = mistral_response
                    llm_provider_recs = "Mistral (fallback)"
                    logger.info(f"Successfully used Mistral as fallback for AI recommendations (Lang: {language_code}).")
                else:
                    logger.error(f"Mistral fallback for AI recommendations returned empty response without explicit error (Lang: {language_code}).")
                    error_message_for_recs = "Primary LLM (Gemini) failed/not configured; Mistral fallback for recommendations returned empty."
            else:
                logger.warning(f"Primary LLM failed/not configured for recommendations, and Mistral is not configured (Lang: {language_code}).")
                error_message_for_recs = "Primary LLM (Gemini) failed/not configured for recommendations; Mistral fallback not configured."

        if not ai_response_str:
            logger.error(f"All LLM attempts for AI recommendations failed (Lang: {language_code}). Final error state: {error_message_for_recs}")
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

            # Strategic Recommendations
            strategic_recs = recommendations_data.get('strategic_recommendations', [])
            if strategic_recs:
                formatted_recommendations.append(title_strategic_recommendations)
                for i, rec in enumerate(strategic_recs, 1):
                    category = rec.get('category', 'General')
                    title = rec.get('title', 'Recommendation')
                    description = rec.get('description', '')
                    priority = rec.get('priority', 'Medium')
                    difficulty = rec.get('implementation_difficulty', 'Medium')
                    based_on_data = rec.get('based_on_data', '')

                    formatted_recommendations.append(f"#### {i}. {title} ({category})")
                    
                    priority_label = language_manager.get_text("rec_strategic_priority_label", language_code, fallback="Priority")
                    implementation_label = language_manager.get_text("rec_strategic_implementation_label", language_code, fallback="Implementation")
                    formatted_recommendations.append(f"**{priority_label}**: {priority} | **{implementation_label}**: {difficulty}")

                    if based_on_data:
                        data_source_label = language_manager.get_text("rec_strategic_data_source_label", language_code, fallback="Data Source")
                        formatted_recommendations.append(f"**{data_source_label}**: {based_on_data}")
                    formatted_recommendations.append(description)
                    formatted_recommendations.append("")

            # SEO Optimization Insights
            # FIX: Refactored this section for clearer, more professional report formatting.
            # Instead of concatenating distinct fields into one string, each piece of data is now presented separately.
            seo_recs = recommendations_data.get('seo_optimization_insights', [])
            if seo_recs:
                formatted_recommendations.append(title_seo_optimization_insights)
                default_focus_area_text = language_manager.get_text("rec_seo_default_focus_area", language_code, fallback="SEO Suggestion")
                for rec in seo_recs:
                    focus_area = rec.get('focus_area', default_focus_area_text)
                    current_issue = rec.get('observed_issue_or_opportunity', '')
                    insight = rec.get('insight_derived', '')
                    strategic_action = rec.get('example_strategic_action')
                    supporting_data = rec.get('supporting_data_points')
                    expected_impact = rec.get('potential_impact_if_addressed', '')
                    
                    formatted_recommendations.append(f"#### {focus_area}")

                    if current_issue:
                        observed_issue_label = language_manager.get_text("rec_seo_observed_issue_label", language_code, fallback="Observed Issue/Opportunity")
                        formatted_recommendations.append(f"**{observed_issue_label}**: {current_issue}")
                    
                    if insight:
                        insight_label = language_manager.get_text("rec_seo_insight_label", language_code, fallback="Insight")
                        formatted_recommendations.append(f"**{insight_label}**: {insight}")
                    
                    if strategic_action:
                        action_label = language_manager.get_text("rec_seo_strategic_action_label", language_code, fallback="Strategic Action Example")
                        formatted_recommendations.append(f"**{action_label}**: {strategic_action}")

                    if supporting_data:
                        supporting_data_label = language_manager.get_text("common_supporting_data_label", language_code, fallback="Supporting Data")
                        data_points_str = ', '.join(supporting_data)
                        formatted_recommendations.append(f"**{supporting_data_label}**: {data_points_str}")
                    
                    if expected_impact:
                        potential_impact_label = language_manager.get_text("rec_seo_potential_impact_label", language_code, fallback="Potential Impact")
                        formatted_recommendations.append(f"**{potential_impact_label}**: {expected_impact}")
                    
                    formatted_recommendations.append("")


            # Target Audience Personas
            personas = recommendations_data.get('target_audience_personas', [])
            if personas:
                formatted_recommendations.append(title_target_audience_personas)
                persona_item_prefix = language_manager.get_text("persona_item_prefix_label", language_code, fallback="Persona")
                for i, persona in enumerate(personas, 1):
                    formatted_recommendations.append(f"#### {persona_item_prefix} {i}: {persona.get('persona_name', 'N/A')}")
                    
                    if persona.get('demographics'):
                        label = language_manager.get_text("persona_demographics_label", language_code, fallback="Demographics")
                        formatted_recommendations.append(f"**{label}**: {persona.get('demographics')}")
                    if persona.get('occupation_role'):
                        label = language_manager.get_text("persona_occupation_role_label", language_code, fallback="Occupation/Role")
                        formatted_recommendations.append(f"**{label}**: {persona.get('occupation_role')}")
                    if persona.get('goals_related_to_site'):
                        label = language_manager.get_text("persona_goals_label", language_code, fallback="Goals (related to site)")
                        formatted_recommendations.append(f"**{label}**: {'; '.join(persona.get('goals_related_to_site'))}")
                    if persona.get('pain_points_challenges'):
                        label = language_manager.get_text("persona_pain_points_label", language_code, fallback="Pain Points/Challenges")
                        formatted_recommendations.append(f"**{label}**: {'; '.join(persona.get('pain_points_challenges'))}")
                    if persona.get('motivations_for_using_site'):
                        label = language_manager.get_text("persona_motivations_label", language_code, fallback="Motivations for Using Site")
                        formatted_recommendations.append(f"**{label}**: {'; '.join(persona.get('motivations_for_using_site'))}")
                    if persona.get('information_sources'):
                        label = language_manager.get_text("persona_info_sources_label", language_code, fallback="Information Sources")
                        formatted_recommendations.append(f"**{label}**: {'; '.join(persona.get('information_sources'))}")
                    if persona.get('key_message_for_persona'):
                         label = language_manager.get_text("persona_key_message_label", language_code, fallback="Key Message")
                         formatted_recommendations.append(f"**{label}**: {persona.get('key_message_for_persona')}")
                    formatted_recommendations.append("")

            # Content Strategy Insights
            content_insights = recommendations_data.get('content_strategy_insights', [])
            if content_insights:
                formatted_recommendations.append(title_content_strategy_insights)
                insight_item_prefix = language_manager.get_text("rec_content_insight_item_prefix_label", language_code, fallback="Insight")
                for i, insight_data in enumerate(content_insights, 1):
                    insight = insight_data.get('insight_statement', '')
                    supporting_data_val = insight_data.get('supporting_data', '')
                    implications_val = insight_data.get('implications_for_content', '')

                    formatted_recommendations.append(f"#### {insight_item_prefix} {i}: {insight}")
                    if supporting_data_val:
                        label = language_manager.get_text("common_supporting_data_label", language_code, fallback="Supporting Data")
                        formatted_recommendations.append(f"**{label}**: {supporting_data_val}")
                    if implications_val:
                        label = language_manager.get_text("rec_cs_implications_label", language_code, fallback="Implications for Content")
                        formatted_recommendations.append(f"**{label}**: {implications_val}")

                    illustrative_opp = insight_data.get('illustrative_content_opportunity')
                    if illustrative_opp:
                        label_opp_title = language_manager.get_text("rec_cs_illustrative_opp_label", language_code, fallback="Illustrative Content Opportunity:")
                        formatted_recommendations.append(f"**{label_opp_title}**")
                        
                        label_type = language_manager.get_text("rec_cs_opp_type_label", language_code, fallback="Type")
                        formatted_recommendations.append(f"- **{label_type}**: {illustrative_opp.get('opportunity_type', 'N/A')}")
                        
                        label_desc = language_manager.get_text("rec_cs_opp_description_label", language_code, fallback="Description")
                        formatted_recommendations.append(f"  - **{label_desc}**: {illustrative_opp.get('description', '')}")

                        label_persona_align = language_manager.get_text("rec_cs_opp_target_persona_label", language_code, fallback="Target Persona Alignment")
                        formatted_recommendations.append(f"  - **{label_persona_align}**: {illustrative_opp.get('target_persona_alignment', '')}")
                        
                        if illustrative_opp.get('potential_topics_or_angles'):
                            topics = "; ".join(illustrative_opp.get('potential_topics_or_angles', []))
                            label_topics = language_manager.get_text("rec_cs_opp_potential_topics_label", language_code, fallback="Potential Topics/Angles")
                            formatted_recommendations.append(f"  - **{label_topics}**: {topics}")

                        label_justification = language_manager.get_text("rec_cs_opp_justification_label", language_code, fallback="Justification")
                        formatted_recommendations.append(f"  - **{label_justification}**: {illustrative_opp.get('justification_based_on_data', '')}")
                    formatted_recommendations.append("")

            if not formatted_recommendations:
                logger.warning(f"AI ({llm_provider_recs}) generated data for recommendations (Lang: {language_code}), but no specific sections were populated based on the new prompt structure.")
                return f"AI ({llm_provider_recs}) generated data, but it was not in the expected format or was empty after processing the new structure."

            logger.info(f"Successfully generated and formatted AI-powered recommendations using {llm_provider_recs} (Lang: {language_code}).")
            return "\n".join(formatted_recommendations)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI recommendations JSON from {llm_provider_recs} (Lang: {language_code}): {e}. Raw response: '{ai_response_str[:500]}'")
            return f"AI recommendations were generated by {llm_provider_recs} but could not be parsed properly. Raw response (first 500 chars): {ai_response_str[:500]}..."

    except Exception as e:
        logger.error(f"Error generating AI recommendations (Lang: {language_code}): {e}", exc_info=True)
        return f"An error occurred while generating AI recommendations: {str(e)}"