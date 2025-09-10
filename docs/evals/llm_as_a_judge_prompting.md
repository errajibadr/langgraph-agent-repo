# LLM As A Judge Best Practices

Now, we need to write an evaluator that will compare our research brief against the success criteria that we have specified for each example. For this, we'll use an LLM-as-judge. You can find some useful tips for writing llm-as-judge evaluators here, which include:

## Role Definition with Expertise Context

- Defined specific expert roles ("research brief evaluator", "meticulous auditor")
- Specialized the role to the specific evaluation domain

## Clear Task Specification

- Binary pass/fail judgments (avoiding complex multi-dimensional scoring)
- Explicit task boundaries and objectives
- Focus on actionable evaluation criteria

## Rich Contextual Background

- Provide domain-specific context about research brief quality
- Explain the importance of accurate evaluation
- Connect evaluation outcomes to downstream consequences

## Structured XML Organization

- Used semantic XML tags for different sections
- Clear separation of role, task, context, inputs, guidelines, and outputs
- Improved prompt parsing and comprehension

## Comprehensive Guidelines with Examples

- Detailed PASS/FAIL criteria with specific conditions
- Multiple concrete examples showing correct judgments
- 3-4 examples per prompt covering different scenarios
- Both positive and negative examples for each judgment type
- Edge case handling and decision boundary clarification

## Explicit Output Instructions

- Clear guidance on how to apply the evaluation criteria
- Instructions for handling ambiguous cases
- Emphasis on consistency and systematic evaluation

## Bias Reduction Techniques

- "Strict but fair" guidance to balance precision and recall
- "When in doubt, lean toward FAIL" for conservative evaluation
- Systematic evaluation process to reduce subjective variation