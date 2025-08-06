from langgraph.graph import END, StateGraph
from typing import TypedDict, Literal
from langchain_core.prompts import ChatPromptTemplate
from services.llms import llm
from services.model import ModelService
from dotenv import load_dotenv
from logger import logger
from schemas import DocumentGrade, GeneratedAnswer, RewrittenQuery
load_dotenv()
from .retrieval_pipeline import retrieval_pipeline

class GraphState(TypedDict):
    query: str
    original_query: str
    metadata: dict
    documents: list
    generation: str
    grade: Literal["yes", "no"]
    logs: list
    retry_count: int


class CRAGService:
    def __init__(self):
        self.model_service = ModelService()
        self.llm = llm
        # Create structured output LLMs for different tasks
        self.grading_llm = llm.with_structured_output(DocumentGrade)
        self.generation_llm = llm.with_structured_output(GeneratedAnswer)
        self.rewriter_llm = llm.with_structured_output(RewrittenQuery)
        self.workflow = self._build_workflow()
    
    def _build_workflow(self):
        workflow = StateGraph(GraphState)

        # Define nodes
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("grade_documents", self.grade_documents)
        workflow.add_node("rewrite_query", self.rewrite_query)
        workflow.add_node("generate", self.generate_answer)

        # Define edges
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            self.decide_next_step,
            {
                "generate": "generate",
                "rewrite": "rewrite_query",
                "quit": "generate"
            }
        )
        workflow.add_edge("rewrite_query", "retrieve")
        workflow.add_edge("generate", END)

        return workflow.compile()


    def retrieve(self, state: GraphState):
        print("---RETRIEVING DOCUMENTS FROM WEAVIATE---")

        retry_count = state.get("retry_count", 0)
        query = state["query"]

        # Log the retrieval attempt
        logs = state.get("logs", [])
        if retry_count == 0:
            logs.append("Step 2.1: Retrieving documents from database")
        else:
            logs.append(f"Step 2.1: Retry {retry_count} - Retrieving with rewritten query")

        logs.append(f"Query: '{query}'")

        # Use lenient retrieval settings - cast a wide net to capture potentially relevant documents
        # The grading step will filter out truly irrelevant content
        relevant_docs = retrieval_pipeline(state)

        doc_count = len(relevant_docs.get('documents', []))
        logs.append(f"Retrieved {doc_count} documents")
        logs.append("\n")  # Add separator

        return {**relevant_docs, "logs": logs}

    
    def grade_documents(self, state: GraphState):
        print("---GRADING DOCUMENT QUALITY---")
        query = state["query"]
        documents = state["documents"]
        logs = state.get("logs", [])

        if not documents:
            logs.append("Step 2.2: No documents found - marking as not relevant")
            logs.append("\n")
            return {"grade": "no", "logs": logs}

        logs.append("Step 2.2: Evaluating document relevance")

        # Prepare document content
        doc_text = documents

        # LLM to grade document relevance with structured output
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert document relevance grader for a Retrieval-Augmented Generation (RAG) system. Your task is to assess whether retrieved documents contain information that can help answer a user's question.

GRADING CRITERIA:
- Be LENIENT in your assessment - even partial relevance is valuable
- Look for ANY information that could contribute to answering the question
- Consider both direct answers and contextual information that supports the answer
- Documents don't need to contain the complete answer, just relevant pieces
- Even tangentially related information can be useful for comprehensive responses

EXAMPLES OF WHEN TO SAY 'YES':
- Documents contain partial information about the topic
- Documents provide background context relevant to the question
- Documents mention related concepts or terminology
- Documents contain data, statistics, or examples related to the topic
- Documents discuss similar scenarios or cases

EXAMPLES OF WHEN TO SAY 'NO':
- Documents are about completely different topics with no connection

Provide your assessment with reasoning for the decision."""),
            ("human", """Evaluate if these retrieved documents can help answer the user question.

User question: {query}

Retrieved documents:
{docs}

Can these documents be used to answer the question?""")
        ])

        chain = prompt | self.grading_llm
        response = chain.invoke({"query": query, "docs": doc_text})

        grade = response.grade
        print(f"---DOCUMENT GRADE: {grade.upper()}---")

        if grade == "yes":
            logs.append("Result: Documents are relevant for answering the query")
        else:
            logs.append("Result: Documents are not relevant for answering the query")

        logs.append("\n")

        return {"grade": grade, "logs": logs}
    
    def generate_answer(self, state: GraphState):
        print("---GENERATING ANSWER---")

        query = state["query"]
        documents = state["documents"]
        logs = state.get("logs", [])

        context = documents

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert assistant providing comprehensive answers based on retrieved documents. Your task is to synthesize information from the provided context to answer the user's question thoroughly and accurately.

INSTRUCTIONS:
1. Use ONLY the information provided in the context below
2. Provide a detailed, well-structured answer that fully addresses the question
3. Synthesize information from multiple sources when available
4. Include specific details, examples, and data points from the context
5. Organize your response logically with clear explanations
6. If the context contains conflicting information, acknowledge this and present both perspectives
7. If you cannot fully answer the question with the provided context, clearly state what information is missing
8. Do not add information not present in the context
9. Be thorough but concise - aim for completeness without unnecessary verbosity
10. If the context seems only partially relevant, extract whatever useful information is available and clearly indicate the limitations

ADDITIONAL REQUIREMENTS:
- Assess your confidence level in the answer (high/medium/low)
- Identify which sources were primarily used
- Provide a comprehensive answer with supporting details

Context:
{context}"""),
            ("human", "Please provide the best possible answer to this question based on the context provided:\n\nQuestion: {query}")
        ])

        retry_count = state.get("retry_count", 0)
        if retry_count > 0:
            logs.append(f"Step 2.4: Generating answer after {retry_count} query rewrites")
        else:
            logs.append("Step 2.4: Generating answer with initial query")

        chain = prompt | self.generation_llm
        response = chain.invoke({"query": query, "context": context})

        logs.append("Answer generated successfully")

        return {"generation": response.answer, "logs": logs}

    def rewrite_query(self, state: GraphState):
        """Rewrite the query to improve retrieval when documents are not relevant."""
        print("---REWRITING QUERY---")

        original_query = state["original_query"]
        current_query = state["query"]
        retry_count = state.get("retry_count", 0)
        logs = state.get("logs", [])

        logs.append(f"Step 2.3: Rewriting query (attempt {retry_count + 1}/3)")
        logs.append(f"Current query: '{current_query}'")

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert query rewriter for a Retrieval-Augmented Generation (RAG) system. Your task is to rewrite queries that failed to retrieve relevant documents.

REWRITING STRATEGIES:
1. Use synonyms and alternative terminology
2. Break down complex queries into simpler components
3. Add context or domain-specific terms
4. Rephrase using different sentence structures
5. Include related concepts that might be in the documents
6. Make the query more specific or more general as needed

GUIDELINES:
- Preserve the original intent and meaning
- Make the query more likely to match document content
- Use clear, searchable language
- Avoid overly complex or ambiguous phrasing
- Consider different ways the information might be expressed in documents

Original query: {original_query}
Current query: {current_query}
Attempt number: {retry_count}

Provide a rewritten query that is more likely to retrieve relevant documents."""),
            ("human", "Please rewrite this query to improve document retrieval: {current_query}")
        ])

        chain = prompt | self.rewriter_llm
        response = chain.invoke({
            "original_query": original_query,
            "current_query": current_query,
            "retry_count": retry_count + 1
        })

        logs.append(f"New query: '{response.rewritten_query}'")
        logs.append(f"Reasoning: {response.reasoning}")
        logs.append("\n")

        return {
            "query": response.rewritten_query,
            "retry_count": retry_count + 1,
            "logs": logs
        }



    def decide_next_step(self, state: GraphState):
        """Decide whether to generate, rewrite query, or quit based on document grade and retry count."""
        grade = state.get("grade", "no")
        retry_count = state.get("retry_count", 0)
        logs = state.get("logs", [])

        # If documents are good, generate answer
        if grade == "yes":
            return "generate"

        # If documents are not good, check retry count
        if retry_count >= 3:
            logs.append("Maximum retries (3) reached - proceeding with available documents")
            logs.append("\n")
            return "quit"

        # If we haven't reached max retries, rewrite the query
        return "rewrite"
    

    
    def run(self, query: str, metadata: dict):
        # Initialize state
        state = {
            "query": query,
            "original_query": query,  # Keep track of the original query
            "metadata": metadata,
            "documents": [],
            "generation": "",
            "grade": "no",
            "logs": [],
            "retry_count": 0
        }

        # Execute workflow using invoke instead of stream
        result = self.workflow.invoke(state)

        return result


# if __name__ == "__main__":
#     # For local testing
#     import json

#     crag_service = CRAGService()

#     sample_query = "What is the impact of climate change on coastal erosion?"
#     sample_metadata = {
#         "filename": "",   # or set to a valid filename to filter documents
#         "date": ""        # or set to a valid date
#     }

#     result = crag_service.run(sample_query, sample_metadata)

#     print("\n\n========== FINAL OUTPUT ==========")
#     print(f"Query: {sample_query}")
#     print(f"Answer:\n{result['generation']}")
#     print(f"\nSources:")
#     for doc in result['documents']:
#         print(json.dumps(doc["metadata"], indent=2))
