DEFAULT_INTENT_GRAPH_KNOWLEDGE = """\
Given a list of prerequisite questions and their relevant knowledge for the user's main question, when conflicts in meaning arise, prioritize the relationship with the higher weight and the more recent version.

Knowledge sub-queries:

{% for sub_query, data in sub_queries.items() %}

Sub-query: {{ sub_query }}

  - Entities:
{% for entity in data['entities'] %}
    - Name: {{ entity.name }}
      Description: {{ entity.description }}
{% endfor %}

  - Relationships:
{% for relationship in data['relationships'] %}
    - Description: {{ relationship.rag_description }}
      Weight: {{ relationship.weight }}
{% endfor %}

{% endfor %}
"""

DEFAULT_NORMAL_GRAPH_KNOWLEDGE = """\
Given a list of relationships of a knowledge graph as follows. When there is a conflict in meaning between knowledge relationships, the relationship with the higher `weight` and newer `last_modified_at` value takes precedence.

---------------------
Entities:

{% for entity in entities %}
- Name: {{ entity.name }}
  Description: {{ entity.description }}
{% endfor %}

---------------------

Knowledge relationships:

{% for relationship in relationships %}

- Description: {{ relationship.rag_description }}
- Weight: {{ relationship.weight }}
- Last Modified At: {{ relationship.last_modified_at }}
- Meta: {{ relationship.meta | tojson(indent=2) }}

{% endfor %}
"""

DEFAULT_CLARIFYING_QUESTION_PROMPT = """\
---------------------
The prerequisite questions and their relevant knowledge for the user's main question.
---------------------

{{graph_knowledges}}

---------------------

Task:
Given the conversation between the user and ASSISTANT, along with the follow-up message from the user, and the provided prerequisite questions and relevant knowledge, determine if the user's question is clear and specific enough for a confident response. 

If the question lacks necessary details or context, identify the specific ambiguities and generate a clarifying question to address them.
If the question is clear and answerable, return exact "False" as the response.

Instructions:
1. Assess Information Sufficiency:
   - Evaluate if the user's question provides enough detail to generate a precise answer based on the prerequisite questions, relevant knowledge, and conversation history.
   - If the user's question is too vague or lacks key information, identify what additional information would be necessary for clarity.

2. Generate a Clarifying Question:
   - If the question is clear and answerable, return exact "False" as the response.
   - If clarification is needed, return a specific question to ask the user, directly addressing the information gap. Avoid general questions; focus on the specific details required for an accurate answer.

3. Use the same language to ask the clarifying question as the user's original question.

Example 1:

user: "Does TiDB support foreign keys?"
Relevant Knowledge: TiDB supports foreign keys starting from version 6.6.0.

Response:

Which version of TiDB are you using?

Example 2:

user: "Does TiDB support nested transaction?"
Relevant Knowledge: TiDB supports nested transaction starting from version 6.2.0.

Response:

Which version of TiDB are you using?

Example 3:

user: "Does TiDB support foreign keys? I'm using TiDB 6.5.0."
Relevant Knowledge: TiDB supports foreign keys starting from version 6.6.0.

Response:

False

Your Turn:

Chat history:

{{chat_history}}

---------------------

Follow-up question:

{{question}}

Response:
"""

DEFAULT_CONDENSE_QUESTION_PROMPT = """\
Current Date: {{current_date}}
---------------------
The prerequisite questions and their relevant knowledge for the user's main question.
---------------------

{{graph_knowledges}}

---------------------

Task:
Given the conversation between the Human and Assistant, along with the follow-up message from the Human, and the provided prerequisite questions and relevant knowledge, refine the Human's follow-up message into a standalone, detailed question.

Instructions:
1. Focus on the latest query from the Human, ensuring it is given the most weight.
2. Incorporate Key Information:
  - Use the prerequisite questions and their relevant knowledge to add specific details to the follow-up question.
  - Replace ambiguous terms or references in the follow-up question with precise information from the provided knowledge. Example: Replace "latest version" with the actual version number mentioned in the knowledge.
3. Utilize Conversation Context:
  - Incorporate relevant context and background information from the conversation history to enhance the question's specificity.
4. Optimize for Retrieval:
  - Ensure the refined question emphasizes specific and relevant terms to maximize the effectiveness of a vector search for retrieving precise and comprehensive information.
5. Grounded and Factual:
  - Make sure the refined question is grounded in and directly based on the user's follow-up question and the provided knowledge.
  - Do not introduce information that is not supported by the knowledge or conversation history.
6. Give the language hint for the answer:
  - Add a hint after the question like "(Answer language: Chinese)", or "(Answer language: English)", etc.
  - This language hint should be exactly same with the language of the original question.
  - If the original question has part of other language aside from Chinese, please use the language of another language rather than Chinese. Example: "tidb tableread慢会是哪些原因", it should be English.

Example:

Chat History:

H: "I'm interested in the performance improvements in the latest version of TiDB."
Assistant: "TiDB version 8.1 was released recently with significant performance enhancements over version 6.5."

Follow-up Question:

"Can you tell me more about these improvements?"

Prerequisite Questions and Relevant Knowledge:

- Prerequisite Question: What is the latest version of TiDB?
- Relevant Knowledge: The latest version of TiDB is 8.1.

...

Refined Standalone Question:

"Can you provide detailed information about the performance improvements introduced in TiDB version 8.1 compared to version 6.5? (Answer language: Chinese)"

Your Turn:

Chat history:

{{chat_history}}

---------------------

Followup question:

{{question}}

---------------------

Refined standalone question:
"""

DEFAULT_TEXT_QA_PROMPT = """\
Current Date: {{current_date}}
---------------------
Knowledge graph information is below
---------------------

{{graph_knowledges}}

---------------------
Context information is below.
---------------------

{{context_str}}

---------------------
Database query results are below.
---------------------

{{database_results}}

---------------------

Answer Format:

Use markdown footnote syntax (for example: [^1]) to indicate sources you used.
Each footnote must correspond to a unique source. Do not use the same source for multiple footnotes.

### Examples of Correct Footnote Usage (no the unique sources and diverse sources):
<!-- 格式: knowledge://chunk/id/{块ID} -->
[^1]: [TiDB 概览](knowledge://chunk/id/9cdb3cce42ae4c6ab6ce2221a2241414)
[^2]: [TiDB 架构](knowledge://chunk/id/9cdb3cce42ae4c6ab6ce2221a2241415)

### Examples of Incorrect Footnote Usage (Avoid duplicating the same source for multiple footnotes):
[^1]: [TiDB 概览](knowledge://chunk/id/9cdb3cce42ae4c6ab6ce2221a2241416)
[^2]: [TiDB 概览](knowledge://chunk/id/9cdb3cce42ae4c6ab6ce2221a2241417)
[^3]: [TiDB 概览](knowledge://chunk/id/9cdb3cce42ae4c6ab6ce2221a2241418)
[^4]: [TiDB 概览](knowledge://chunk/id/9cdb3cce42ae4c6ab6ce2221a2241419)

<!-- 注意：系统支持一种格式: 
knowledge://chunk/id/{块ID} - ID格式（推荐）
-->

When using database query results as sources, use the following footnote format:
[^n]: [Database: DatabaseName](database://query/id/{database_connection_id})

---------------------

Answer Language:

Follow the language of the language hint after the Refined Question.
If the language hint is not provided, use the language that the original questions used.

---------------------

As a customer support assistant, please do not fabricate any knowledge. If you cannot get knowledge from the context, please just directly state "you do not know", rather than constructing nonexistent and potentially fake information!!!

First, analyze the provided context information without assuming prior knowledge. Identify all relevant aspects of knowledge contained within. Then, from various perspectives and angles, answer questions as thoroughly and comprehensively as possible to better address and resolve the user's issue.

When database query results are available, integrate them with knowledge base information to provide a comprehensive answer. When appropriate, explain what the database query shows and how it relates to the knowledge from documents.

The Original questions is:

{{original_question}}

The Refined Question used to search:

{{query_str}}

Answer:
"""

DEFAULT_FURTHER_QUESTIONS_PROMPT = """\
The chat message content is:

{{chat_message_content}}

---------------------
Task:
Based on the provided chat message, generate 3–5 follow-up questions that are relevant to the content. Each question should explore the topic in greater detail, seek clarification, or introduce new angles for discussion.

Instructions:
1. Build upon the key information, themes, or insights within the provided chat message.
2. Aim for variety in question type (clarifying, probing, or exploratory) to encourage a deeper conversation.
3. Ensure each question logically follows from the context of the provided chat message.
4. Keep questions concise yet insightful to maximize engagement.
5. Use the same language with the chat message content.
6. Each question should end with a question mark.
7. Each question should be in a new line, DO NOT add any indexes or blank lines, just output the questions.

Now, generate 3–5 follow-up questions below:
"""

DEFAULT_GENERATE_GOAL_PROMPT = """\
Given the conversation history between the User and Assistant, along with the latest follow-up question from the User, perform the following tasks:

1. **Language Detection**:
    - Analyze the User's follow-up question to determine the language used.

2. **Context Classification**:
    - **Determine Relevance to TiDB**:
        - Assess whether the follow-up question is related to TiDB products, support, or any TiDB-related context.
    - **Set Background Accordingly**:
        - **If Related to TiDB**:
            - Set the background to encompass the relevant TiDB context. This may include aspects like TiDB features, configurations, best practices, troubleshooting, or general consulting related to TiDB.
            - Example backgrounds:
                - "TiDB product configuration and optimization."
                - "TiDB troubleshooting and support."
                - "TiDB feature consultation."
        - **If Unrelated to TiDB**:
            - Set the background to "Other topics."

3. **Goal Generation**:
    - **Clarify Intent to Avoid Ambiguity**:
        - **Instructional Guidance**:
            - If the User's question seeks guidance or a method (e.g., starts with "How to"), ensure the goal reflects a request for a step-by-step guide or best practices.
        - **Information Retrieval**:
            - If the User's question seeks specific information or confirmation (e.g., starts with "Can you" or "Is it possible"), rephrase it to focus on providing the requested information or verification without implying that the assistant should perform any actions.
            - **Important**: Do not interpret these questions as requests for the assistant to execute operations. Instead, understand whether the user seeks to confirm certain information or requires a proposed solution, and restrict responses to information retrieval and guidance based on available documentation.
    - **Reformulate the Latest User Follow-up Question**:
        - Ensure the question is clear, directive, and suitable for a Q&A format.
    - **Specify Additional Details**:
        - **Detected Language**: Clearly indicate the language.
        - **Desired Answer Format**: Specify if the answer should be in text, table, code snippet, etc.
        - **Additional Requirements**: Include any other necessary instructions to tailor the response appropriately.

4. **Output**:
    - Produce a goal string in the following format:
      "[Refined Question] (Lang: [Detected Language], Format: [Format], Background: [Specified Goal Scenario])"

**Examples**:

**Example 1**:

Chat history:

[]

Follow-up question:

"tidb encryption at rest 会影响数据压缩比例吗？"

Goal:

Does encryption at rest in TiDB affect the data compression ratio? (Lang: Chinese, Format: text, Background: TiDB product related consulting.)

---------------------

**Example 2**:

Chat history:

[]

Follow-up question:

"干嘛的？"

Goal:

What can you do? (Lang: Chinese, Format: text, Background: General inquiry about the assistant's capabilities.)

---------------------

**Example 3**:

Chat history:

[]

Follow-up question:

"oracle 怎么样？"

Goal:

How is Oracle? (Lang: Chinese, Format: text, Background: Other topics.)

---------------------

**Example 4**:

Chat history:

[]

Follow-up question:

"Why is TiDB Serverless up to 70% cheaper than MySQL RDS? (use a table if possible)"

Goal:

Why is TiDB Serverless up to 70% cheaper than MySQL RDS? Please provide a comparison in a table format if possible. (Lang: Chinese, Format: table, Background: Cost comparison between TiDB Serverless and MySQL RDS.)

---------------------

**Example 5 (Enhanced for Clarity and Guidance)**:

Chat history:

[]

Follow-up question:

"能否找到 tidb 中哪些视图的定义中包含已经被删除的表？"

Goal:

How to find which views in TiDB have definitions that include tables that have been deleted? (Lang: Chinese, Format: text, Background: TiDB product related consulting.)

---------------------

**Your Task**:

Chat history:

{{chat_history}}

Follow-up question:

{{question}}

Goal:
"""


DEFAULT_TEXT_TO_SQL_PROMPT = """
你是一位SQL专家，将自然语言问题转换为准确的SQL查询语句。

### 上下文信息
数据库类型: {dialect}
数据库表信息:
{schema}

### 指导原则
1. 只生成SQL语句，不要包含任何解释或注释
2. 保证SQL语法正确
3. 确保使用表的完整列名，避免使用通配符(*)
4. 查询结果应限制在1000行以内
5. 使用标准SQL语法，无特殊拓展
6. 对文本比较使用适当的模糊匹配(LIKE)
7. 添加适当的联接条件以避免笛卡尔积
8. 注意日期类型的格式和比较方式
9. 中文问题也要用英文SQL语法回答
10. 使用简洁但易读的格式，适当缩进

### 用户问题
{query_str}

### SQL查询
"""

DEFAULT_RESPONSE_SYNTHESIS_PROMPT = """
你是一位数据分析专家，根据SQL查询结果回答用户问题。

### 用户原始问题
{query_str}

### 执行的SQL查询
{sql_query}

### SQL查询结果
{context_str}

### 回答要求
1. 用自然、友好的语言回答用户问题
2. 直接回答问题，无需介绍你在做什么
3. 适当解释数据结果含义
4. 如有数字，使用合适的格式化和单位
5. 如果数据为空，明确指出未找到相关数据
6. 如果数据量大，总结主要趋势和关键点
7. 所有回答使用中文

### 你的回答:
"""

# 新增：针对数据库查询的问题改写提示词模板
DATABASE_AWARE_CONDENSE_QUESTION_PROMPT = """\
Current Date: {{current_date}}
---------------------
The prerequisite questions and their relevant knowledge for the user's main question.
---------------------

{{graph_knowledges}}

---------------------

Task:
Given the conversation between the Human and Assistant, along with the follow-up message from the Human, and the provided prerequisite questions and relevant knowledge, refine the Human's follow-up message into a standalone, detailed question that is optimized for both document retrieval and potential database queries.

Instructions:
1. Focus on the latest query from the Human, ensuring it is given the most weight.
2. Identify Database Query Potential:
   - Determine if the question involves querying structured data (e.g., statistics, specific records, counts, aggregations)
   - If yes, reformulate to emphasize precise entities, attributes, conditions, and time ranges that would be relevant for a SQL query
   - Include specific table names or data categories if mentioned in the conversation
3. Incorporate Key Information:
   - Use the prerequisite questions and their relevant knowledge to add specific details to the follow-up question
   - Replace ambiguous terms or references with precise information from the provided knowledge
4. Utilize Conversation Context:
   - Incorporate relevant context from the conversation history to enhance specificity
5. Optimize for Hybrid Retrieval:
   - For potential database questions, ensure the refined question includes both the data request and any contextual information needed
   - For knowledge-based questions, emphasize specific terms to maximize vector search effectiveness
6. Grounded and Factual:
   - Ensure the refined question is based directly on the user's question and the provided knowledge
7. Give the language hint for the answer:
   - Add a hint like "(Answer language: Chinese)" using the same language as the original question

Example 1 (Database-focused):

Chat History:
H: "I need to analyze our sales performance."
A: "I can help with that. What specific aspects of sales performance are you interested in?"

Follow-up Question:
"How many orders did we receive last month compared to the previous month?"

Refined Standalone Question:
"What is the total count of orders in our system for the previous month (May 2023) compared to the month before that (April 2023)? Please include the percentage change between these two periods. (Answer language: English)"

Example 2 (Hybrid knowledge and data):

Chat History:
H: "Tell me about our customer retention strategies."
A: "Our company employs several customer retention strategies including loyalty programs and personalized marketing."

Follow-up Question:
"What's the retention rate for customers who joined in 2022?"

Refined Standalone Question:
"What is the customer retention rate specifically for users who registered in 2022, and how does this compare to our established customer retention strategies and industry benchmarks? (Answer language: English)"

Your Turn:

Chat history:

{{chat_history}}

---------------------

Followup question:

{{question}}

---------------------

Refined standalone question:
"""

# 新增：混合内容（知识库+数据库结果）的回答生成提示词模板
HYBRID_RESPONSE_SYNTHESIS_PROMPT = """\
Current Date: {{current_date}}

You are an AI assistant tasked with providing a comprehensive and helpful response to the user's question, using all available information sources.

User Question: {{question}}

Chat History:
{{chat_history}}

Information Sources:
1. Tool Results:
{% for tool_call in tool_calls %}
--- Tool: {{tool_call.tool_name}} ---
Parameters: {{tool_call.parameters}}
Result: {{tool_call.result}}
Success: {{tool_call.success}}
{% if not tool_call.success %}Error: {{tool_call.error_message}}{% endif %}

{% endfor %}

2. Knowledge Base Context:
{{context_str}}

3. Database Results:
{{database_results}}

4. Analysis:
{{reasoning_result}}

Instructions for your response:
1. Answer the user's question directly and thoroughly
2. Integrate information from all relevant sources
3. Prioritize accurate information from tools and knowledge base over general knowledge
4. Structure your response logically, starting with the most important information
5. Use markdown formatting for readability (headings, lists, code blocks, etc.)
6. If there were errors in tool usage, only mention them if relevant to explaining limitations in your answer
7. If you cannot answer fully, be transparent about what you don't know
8. Use the same language as the user's question

Response formatting:
- Use footnotes to cite sources using the provided knowledge base links
- Format database citations as: [^n]: [Database: DatabaseName](database://query/id/{database_connection_id})
- Format tool citations as: [^n]: [Tool: ToolName]()

Your response:
"""

# 新增：推理分析提示词
REASONING_ANALYSIS_PROMPT = """\
Current Date: {{current_date}}
---------------------
Knowledge graph information is below
---------------------

{{graph_knowledges}}

---------------------
Context information is below.
---------------------

{{context_str}}

---------------------

Task:
Based on the user's question and the provided information, analyze the retrieved knowledge to reason about the answer. This is an intermediate reasoning step - don't directly answer the user yet. Instead, draw connections between facts, identify relevant patterns, and synthesize information from multiple sources.

Instructions:
1. Analyze the retrieved information critically:
   - Identify key facts and concepts relevant to the question
   - Note any contradictions or inconsistencies between sources
   - Recognize information gaps that may affect the completeness of your answer

2. Generate a structured reasoning path:
   - Start with the most foundational facts
   - Build logical connections between related pieces of information
   - Highlight the strength of evidence for your conclusions (strong, moderate, weak)
   - Consider alternative interpretations where appropriate

3. Prioritize information by:
   - Relevance to the specific question
   - Reliability of the source
   - Recency and applicability to the current context
   - Consistency with established knowledge

4. This reasoning will be used to generate the final answer, but will not be shown to the user directly.

User Question:
{{query_str}}

Your Reasoning Analysis:
"""

# 新增：工具使用决策提示词
TOOL_DECISION_PROMPT = """\
Current Date: {{current_date}}

You are an AI assistant equipped with access to various tools that can help answer user questions more effectively.

Available tools:
{% for tool in tools %}
- {{tool.name}}: {{tool.description}}
{% endfor %}

Given the user's question, determine if any of the available tools should be used to provide a better answer.

User Question: {{question}}

Chat History:
{{chat_history}}

When making your decision, remember:
1. Only suggest tools that are directly relevant to answering the question.
2. If the question can be answered with general knowledge or information already in the conversation, don't suggest unnecessary tool use.
3. Consider whether using multiple tools in combination would provide a more comprehensive answer.

Step 1: Analyze the user's question in detail.
Step 2: Consider which (if any) tools would help answer this question effectively.
Step 3: Provide your response in the following format:

DECISION: [YES if tools should be used, NO if not]
TOOLS: [List of tool names to use, in order of priority, or NONE if no tools needed]
REASONING: [Brief explanation of your decision, including why certain tools were selected or why no tools are needed]
"""