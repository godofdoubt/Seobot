
import json
# Removed streamlit import as language_code is passed directly

def build_ai_recommendations_prompt(website_data_summary: dict, language_code: str = "en") -> str:
    # --- START MODIFICATION for persona count ---
    if language_code == "tr":
        language_instruction = "Yanıtınızı Türkçe verin. "
        persona_instruction_detail = "öncelikle 5-7 farklı hedef kitle personası tanımlayın."
        persona_critical_requirement_detail = "Verilen verilere dayanarak en az 5, ideal olarak 5-7 adet detaylı `target_audience_personas` oluşturun."
    else:
        language_instruction = "" # Default is English
        persona_instruction_detail = "first, define 5-7 distinct target audience personas."
        persona_critical_requirement_detail = "Generate at least 5, ideally 5-7 detailed `target_audience_personas`"
    # --- END MODIFICATION for persona count ---

    """
    Build the comprehensive AI recommendations prompt focused on insights.

    Args:
        website_data_summary: Dictionary containing complete website analysis data
        language_code: Language code for the response (e.g., "en", "tr")

    Returns:
        Complete prompt string for AI recommendations
    """
    return f"""{language_instruction}
    Based on the comprehensive SEO and content analysis of this website, {persona_instruction_detail} Then, provide strategic recommendations and highlight key insights with illustrative examples of how to leverage them for SEO and content improvement. The focus is on showcasing a deep understanding of the data and its implications, generating actionable insights rather than exhaustive lists of tasks.

    WEBSITE ANALYSIS DATA:
    {json.dumps(website_data_summary, indent=2, ensure_ascii=False)}

    Generate recommendations and insights in the following JSON structure. For sections focusing on derived insights (`seo_optimization_insights`, `content_strategy_insights`), provide only 1-2 high-impact, illustrative examples for each, focusing on the 'why' and 'so what' derived from the data:

    {{
        "target_audience_personas": [ // Ensure you generate AT LEAST 5 personas here.
            {{
                "persona_name": "string (e.g., 'Tech-Savvy Tom', 'Budget-Conscious Brenda', 'Araştırmacı Ayşe')",
                "demographics": "string (e.g., '25-35, Urban, Early Adopter', '40-55, Suburban, Value Seeker')",
                "occupation_role": "string (e.g., 'Software Developer', 'Small Business Owner', 'Pazarlama Müdürü')",
                "goals_related_to_site": ["string (what they want to achieve that this website can help with)"],
                "pain_points_challenges": ["string (challenges they face that this website's content/products can solve)"],
                "motivations_for_using_site": ["string (why they would choose this site/product over others)"],
                "information_sources": ["string (where they typically look for information - e.g., Google, Social Media, Forums)"],
                "key_message_for_persona": "string (a concise message that would resonate with this persona based on the site's offerings)"
            }}
        ],
        "strategic_recommendations": [
            {{
                "category": "string (e.g., 'SEO Improvement', 'Content Strategy Enhancement', 'User Experience Optimization', 'Site Architecture Refinement')",
                "title": "string (brief title for the strategic recommendation)",
                "description": "string (detailed explanation of the strategic direction, its importance based on data, and broad strokes on how to approach it)",
                "priority": "string (High/Medium/Low)",
                "implementation_difficulty": "string (Easy/Medium/Hard - for acting on the strategy)",
                "based_on_data": "string (specific data point, metric, or qualitative observation from the website_data_summary that led to this recommendation)"
            }}
        ],
        "seo_optimization_insights": [ // Provide 1-2 illustrative examples
            {{
                "focus_area": "string (e.g., 'Keyword Opportunities', 'Technical SEO Gaps', 'On-Page Optimization Insights', 'Local SEO Potential')",
                "observed_issue_or_opportunity": "string (specific observation from the data, e.g., 'Website ranks on page 2 for 'sustainable energy solutions' but has low click-through rate')",
                "insight_derived": "string (what this observation implies for SEO strategy, e.g., 'There's an opportunity to capture more traffic for a relevant, high-intent keyword by improving meta descriptions and on-page relevance for existing content, or by creating new targeted content.')",
                "potential_impact_if_addressed": "string (e.g., 'Significant increase in organic traffic and qualified leads for 'sustainable energy solutions' related queries')",
                "supporting_data_points": ["string (e.g., 'Keyword 'sustainable energy solutions': Search Vol 1200/mo, Current Avg. Position 15, CTR 1.2%', 'Page /solutions/sustainable-energy: Bounce Rate 70%')"],
                "example_strategic_action": "string (A high-level strategic action illustrating how to leverage this insight, e.g., 'Revise meta title/description for /solutions/sustainable-energy to be more compelling and CTR-focused, and explore creating a comprehensive guide on 'The Benefits of Sustainable Energy Solutions for Businesses' targeting 'Eco-Conscious CEO'.')"
            }}
        ],
        "content_strategy_insights": [ // Provide 1-2 illustrative examples
            {{
                "insight_statement": "string (key insight about content strategy based on analysis, e.g., 'The current blog content lacks practical, case-study driven examples, which 'Problem-Solver Paula' persona actively seeks.')",
                "supporting_data": "string (specific data that supports this insight, e.g., 'Low engagement on theoretical articles (avg_time_on_page < 30s), high bounce rate (80%) on such pages. Persona 'Problem-Solver Paula' goals include 'finding proven solutions'. Top performing competitor content features case studies.')",
                "implications_for_content": "string (what this means for future content creation or existing content revision, e.g., 'Future content should incorporate more real-world examples and case studies to improve engagement and better serve 'Problem-Solver Paula'. Existing theoretical content could be enhanced with practical application sections or links to new case studies.')",
                "illustrative_content_opportunity": {{ // For the example insight, provide 1 example content opportunity
                    "opportunity_type": "string (e.g., 'New Content Theme/Format', 'Content Repurposing for Different Personas', 'Tone Adjustment for Key Segments', 'Format Diversification to Improve Engagement')",
                    "description": "string (Detailed description of the content opportunity, e.g., 'Develop a series of in-depth case studies showcasing successful client outcomes or problem-solving using the website's products/services. Focus on tangible results and quantifiable benefits.')",
                    "target_persona_alignment": "string (Which defined persona this opportunity primarily aligns with and why, e.g., ''Problem-Solver Paula', as this directly addresses her need for proven solutions and practical applications, mitigating her pain point of information overload with theoretical content.')",
                    "potential_topics_or_angles": ["string (Examples of topics or angles stemming from this opportunity, e.g., 'Case Study: How Company X Reduced Operational Costs by 20% with Our Solution', 'From Challenge to Triumph: A Deep Dive into Project Y's Success Story')"],
                    "justification_based_on_data": "string (How this opportunity addresses a gap or leverages a strength found in the data, e.g., 'Addresses low engagement on current theoretical content and aligns with 'Problem-Solver Paula's' information-seeking behavior and goals. Competitor analysis also indicates success with this content format for similar audiences.')"
                }}
            }}
        ]
    }}

    CRITICAL REQUIREMENTS:

    1.  **Language Adherence**: The entire response, including all JSON keys and string values (persona names, descriptions, insights, etc.), MUST be in the language specified at the beginning of this prompt ({'Turkish' if language_code == 'tr' else 'English'}). If the instruction is to respond in Turkish, ensure all output is in Turkish. Otherwise, use English.

    2.  **Persona Definition First**: {persona_critical_requirement_detail}. These personas should inform subsequent recommendations and insights. You MUST generate AT LEAST 5 personas.

    3.  **Data-Driven Insights**: ALL recommendations and insights MUST be based on the actual `technical_statistics` and `website_analysis_data` provided. Reference specific metrics, issues, or opportunities found in the data.

    4.  **Illustrative Examples for Insights**: For `seo_optimization_insights` and `content_strategy_insights`, provide only 1-2 carefully selected, high-impact examples for each category. These examples should demonstrate a strong analytical link to the input data, explain the insight's significance, and suggest a strategic direction to leverage it, targeting relevant personas. Focus on the "why" and "so what".

    5.  **Strategic Focus Areas**: Strategic recommendations and insights should aim to cover (where data supports):
        - SEO technical issues (alt text coverage, mobile optimization, site speed)
        - Content gaps and opportunities identified from keyword analysis (and relevant to personas)
        - User experience improvements based on site structure or observed user behavior
        - Conversion optimization opportunities (considering persona motivations and site goals)

    6.  **Specific Technical Issues to Consider**: Ensure strategic recommendations and `seo_optimization_insights` consider these if present in data:
        - Alt text coverage percentage
        - Mobile responsiveness issues
        - Site structure and navigation problems
        - Page loading performance
        - Internal linking opportunities/issues
        - Broken links or crawl errors

    7.  **Content Strategy Insights Requirements**:
        - Illustrate how insights can address content gaps or opportunities from keyword analysis relevant to defined personas.
        - Consider target personas and topic categories found when framing insights and content opportunities.
        - If suggesting improvements related to existing content, use specific URLs when highly relevant to illustrate the point.

    8.  **Illustrative Insight Examples Must Include**:
        - Specific data points from the analysis that led to the insight.
        - Clear explanation of the insight and its strategic implication.
        - Potential impact or opportunity if acted upon.
        - Which persona the insight/opportunity is most relevant to, if applicable.
        - An example of a strategic action or content direction, not a granular, prescriptive task.

    9.  **No Generic Advice**: Every recommendation and insight must reference specific data points from the analysis. Avoid generic SEO or content advice not tied to the actual website data.

    10. **Prioritization**: Rank `strategic_recommendations` by potential impact and implementation difficulty. Insights provided as examples should ideally be high-impact.

    Output ONLY the JSON object with no additional text, markdown, or formatting.
    """
