from langgraph.graph import END, StateGraph
from typing import TypedDict, Literal
from langchain_core.prompts import ChatPromptTemplate
from services.llms import llm
from services.model import ModelService
from dotenv import load_dotenv
from logger import logger
from schemas import DocumentGrade, GeneratedAnswer
load_dotenv()
from .retrieval_pipeline import retrieval_pipeline

class GraphState(TypedDict):
    query: str
    metadata: dict
    documents: list
    generation: str
    grade: Literal["yes", "no"]


class CRAGService:
    def __init__(self):
        self.model_service = ModelService()
        self.llm = llm
        # Create structured output LLMs for different tasks
        self.grading_llm = llm.with_structured_output(DocumentGrade)
        self.generation_llm = llm.with_structured_output(GeneratedAnswer)
        self.workflow = self._build_workflow()
    
    def _build_workflow(self):
        workflow = StateGraph(GraphState)

        # Define nodes
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("grade_documents", self.grade_documents)
        workflow.add_node("generate", self.generate_answer)

        # Define edges
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            self.decide_to_generate,
            {
                "yes": "generate",
                "no": "generate"
            }
        )
        workflow.add_edge("generate", END)

        return workflow.compile()


    def retrieve(self, state: GraphState):
        print("---RETRIEVING DOCUMENTS FROM WEAVIATE---")

        # Use lenient retrieval settings - cast a wide net to capture potentially relevant documents
        # The grading step will filter out truly irrelevant content
        relevant_docs = retrieval_pipeline(state)
        logger.info(f"Retrieved documents: {relevant_docs}")
        return relevant_docs

    
    def grade_documents(self, state: GraphState):
        print("---GRADING DOCUMENT QUALITY---")
        query = state["query"]
        documents = state["documents"]
        
        if not documents:
            return {"grade": "no"}
        
        # Prepare document content
        doc_text = documents
        logger.info("Retrieved documents: %s", doc_text)
        
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
        logger.info(f"Structured grading response: {response}")

        grade = response.grade
        print(f"---DOCUMENT GRADE: {grade.upper()}---")
        return {"grade": grade}
    
    def generate_answer(self, state: GraphState):
        print("---GENERATING ANSWER---")

        query = state["query"]
        documents = state["documents"]

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

        chain = prompt | self.generation_llm
        response = chain.invoke({"query": query, "context": context})

        return {"generation": response.answer}
    


    
    def decide_to_generate(self, state: GraphState):
        grade = state.get("grade", "no")

        # If documents are good, generate
        if grade == "yes":
            return "yes"

        # If documents are not good, still generate with what we have
        return "no"
    

    
    def run(self, query: str, metadata: dict):
        # Initialize state
        state = {
            "query": query,
            "metadata": metadata,
            "documents": [],
            "generation": "",
            "grade": "no"
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
