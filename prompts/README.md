# Prompts Directory

This directory contains all the prompts used by the OpenAI Podcast Generator. Each prompt is stored in a separate text file for easy editing and management.

## Available Prompts

### Core Podcast Generation Prompts

- **`podcast-script-system.txt`** - System prompt that defines the AI's role as a host for "the PivotPoint Podcast" - a fast-paced, engaging cybersecurity podcast. Includes built-in intro/outro format.

- **`podcast-script-user.txt`** - User prompt template that provides the news articles and instructions for creating the podcast script.

### Article Analysis Prompts

- **`article-analysis-system.txt`** - System prompt for analyzing cybersecurity articles and selecting the most interesting ones by category. Defines criteria for article selection including impact, novelty, industry relevance, and actionable intelligence.

- **`article-analysis-user.txt`** - User prompt template for article analysis that formats articles by category and requests structured analysis with detailed reasoning for each selection.

### Content Templates

- **`podcast-intro.txt`** - Legacy template (not used with PivotPoint Podcast format).

- **`podcast-outro.txt`** - Legacy template (not used with PivotPoint Podcast format).

- **`fallback-script-content.txt`** - Content used when no news articles are available or when AI generation fails.

**Note:** The new PivotPoint Podcast format includes intro/outro directly in the system prompt, so separate intro/outro templates are no longer used.

## How to Edit Prompts

1. **Direct Editing**: Simply open any `.txt` file in this directory and edit the content.

2. **Variable Placeholders**: Some prompts use placeholders that get replaced at runtime:
   - `{date}` - Current date (e.g., "December 21, 2024")
   - `{target_length}` - Target podcast length in minutes
   - `{articles_text}` - Formatted news articles content
   - `{articles_by_category}` - Articles organized by category for analysis

3. **Testing Changes**: After editing a prompt, the changes will take effect on the next run of the application.

## Prompt Guidelines

### For AI Generation Prompts
- Be specific about the desired output format
- Include clear instructions about tone and style
- Specify the target audience
- Provide examples when helpful

### For Article Analysis Prompts
- Define clear selection criteria
- Specify the maximum number of articles per category
- Request detailed reasoning for selections
- Include comparison requirements (why chosen over others)

### For Content Templates
- Keep language professional but conversational
- Ensure consistency with the overall podcast brand
- Consider how the text will sound when spoken aloud

## Article Analysis Workflow

The article analysis system works in the following steps:

1. **Articles Collected**: News articles are gathered from various sources and categorized
2. **GPT Analysis**: Articles are sent to GPT with analysis prompts
3. **Selection Process**: GPT selects up to 3 most interesting articles per category
4. **Reasoning Provided**: For each selection, detailed reasoning is provided
5. **Output Generated**: Results saved to `gpt-article-analysis.txt`

### Customizing Article Selection Criteria

Edit `article-analysis-system.txt` to modify:
- **Priority factors** (impact, novelty, relevance, etc.)
- **Selection guidelines** (recency, credibility, actionability)
- **Audience focus** (executives, analysts, practitioners)
- **Quality thresholds** (minimum impact level, source requirements)

## Adding New Prompts

To add a new prompt:

1. Create a new `.txt` file in this directory
2. Use a descriptive filename (e.g., `threat-intelligence-analysis.txt`)
3. Add the prompt content
4. Update your code to use the new prompt via the `prompt_loader`

Example usage in code:
```python
from utils.prompt_loader import prompt_loader

# Load a simple prompt
content = prompt_loader.load_prompt("your-prompt-name")

# Load and format a prompt with variables
content = prompt_loader.format_prompt("your-prompt-name", 
                                    variable1="value1", 
                                    variable2="value2")
```

## Best Practices

1. **Version Control**: Keep prompts in version control to track changes
2. **Testing**: Test prompt changes with sample data before production use
3. **Documentation**: Document any special formatting or variable requirements
4. **Backup**: Keep backups of working prompts before making major changes
5. **Consistency**: Maintain consistent tone and style across all prompts
6. **Specificity**: Be specific about output format and requirements
7. **Examples**: Include examples in prompts when helpful for clarity

## Article Analysis Output Format

The article analysis generates output in this format:

```
## [CATEGORY NAME]

### Selected Article 1
**Title:** [Article Title]
**URL:** [Article URL]
**Date:** [Article Date]
**Source:** [Article Source]
**Category:** [Category Name]
**Reasoning:** [Detailed explanation of selection rationale]

### Selected Article 2
[Same format...]
```

This structured format makes it easy to:
- Review GPT's selection decisions
- Understand the reasoning behind choices
- Modify selection criteria based on results
- Track which types of articles are consistently selected