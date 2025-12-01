"""
School Research Assistant - Conversation Chain
===============================================
Replaces: ai_engine_premium.py (the GPT analysis part)

"""

import logging
from typing import Optional
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, SystemMessage

# Import based on which LLM we're using
from config_v2 import LLM_PROVIDER, get_model, get_api_keys, LLM_TEMPERATURE, LLM_MAX_TOKENS
from models_v2 import School, ConversationStarter, ConversationStarterResponse
from prompts.templates import get_conversation_starters_prompt

logger = logging.getLogger(__name__)


def get_llm():

    api_keys = get_api_keys()
    
    if LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        
        llm = ChatAnthropic(
            model=get_model("primary"),
            api_key=api_keys["anthropic"],
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
        logger.info(f"✅ Using Claude: {get_model('primary')}")
        return llm
        
    else:  # openai
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model=get_model("primary"),
            api_key=api_keys["openai"],
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
        logger.info(f"✅ Using GPT: {get_model('primary')}")
        return llm


class ConversationChain:
    
    def __init__(self):
        """Initialize the chain with LLM and prompt"""
        self.llm = get_llm()
        self.prompt = get_conversation_starters_prompt()
        self.parser = JsonOutputParser()
        
        # Build the chain using LangChain Expression Language (LCEL)
        # This is the modern way to compose chains
        self.chain = self.prompt | self.llm | self.parser
        
        logger.info("✅ ConversationChain initialized")
    
    def generate(self, school: School, num_starters: int = 5) -> ConversationStarterResponse:

        try:
            # Convert school to text context for the LLM
            school_context = school.to_llm_context()
            
            logger.info(f"🔄 Generating {num_starters} conversation starters for {school.school_name}")
            
            # Run the chain
            result = self.chain.invoke({
                "num_starters": num_starters,
                "school_context": school_context
            })
            
            # Parse into Pydantic model
            response = ConversationStarterResponse(
                conversation_starters=[
                    ConversationStarter(**s) for s in result.get("conversation_starters", [])
                ],
                summary=result.get("summary"),
                sales_priority=result.get("sales_priority", "MEDIUM")
            )
            
            logger.info(f"✅ Generated {len(response.conversation_starters)} starters for {school.school_name}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error generating conversation starters: {e}")
            # Return empty response on error
            return ConversationStarterResponse(
                conversation_starters=[],
                summary=f"Error generating insights: {str(e)}",
                sales_priority="UNKNOWN"
            )
    
    async def agenerate(self, school: School, num_starters: int = 5) -> ConversationStarterResponse:

        try:
            school_context = school.to_llm_context()
            
            logger.info(f"🔄 [ASYNC] Generating starters for {school.school_name}")
            
            # Async invoke
            result = await self.chain.ainvoke({
                "num_starters": num_starters,
                "school_context": school_context
            })
            
            response = ConversationStarterResponse(
                conversation_starters=[
                    ConversationStarter(**s) for s in result.get("conversation_starters", [])
                ],
                summary=result.get("summary"),
                sales_priority=result.get("sales_priority", "MEDIUM")
            )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Async error: {e}")
            return ConversationStarterResponse(
                conversation_starters=[],
                summary=f"Error: {str(e)}",
                sales_priority="UNKNOWN"
            )


def generate_conversation_starters(school: School, num_starters: int = 5) -> list[ConversationStarter]:

    chain = ConversationChain()
    response = chain.generate(school, num_starters)
    return response.conversation_starters


def generate_quick_summary(school: School) -> str:
    """
    Generate a quick 2-sentence summary of a school.
    """
    from prompts.templates import get_quick_summary_prompt
    
    llm = get_llm()
    prompt = get_quick_summary_prompt()
    
    chain = prompt | llm
    
    result = chain.invoke({
        "school_context": school.to_llm_context()
    })
    
    return result.content


if __name__ == "__main__":
    # Test the chain with sample data
    from models_v2 import School, Contact, ContactRole, FinancialData
    
    # Create a test school
    test_school = School(
        urn="100005",
        school_name="Thomas Coram Centre",
        la_name="Camden",
        school_type="Local authority nursery school",
        phase="Nursery",
        address_1="49 Mecklenburgh Square",
        town="London",
        postcode="WC1N 2NY",
        pupil_count=116,
        headteacher=Contact(
            full_name="Ms Perina Holness",
            role=ContactRole.HEADTEACHER,
            title="Ms",
            first_name="Perina",
            last_name="Holness"
        ),
        financial=FinancialData(
            total_teaching_support_spend_per_pupil="Spends £16,067 per pupil (High priority!)",
            comparison_to_other_schools="Spending is higher than 96.7% of similar schools",
            agency_supply_costs="£102 per pupil"
        )
    )
    
    # Test generation
    chain = ConversationChain()
    result = chain.generate(test_school, num_starters=3)
    
    print(f"\n📊 Summary: {result.summary}")
    print(f"🎯 Priority: {result.sales_priority}")
    print(f"\n💬 Conversation Starters:")
    for i, starter in enumerate(result.conversation_starters, 1):
        print(f"\n{i}. {starter.topic}")
        print(f"   {starter.detail}")
