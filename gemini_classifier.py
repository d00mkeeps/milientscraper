# /gemini_classifier.py
from langchain_google_vertexai import ChatVertexAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class CompanyClassification(BaseModel):
    is_relevant: bool = Field(description="True if architecture/engineering/interior design company")
    confidence: float = Field(description="Confidence score 0.0-1.0") 
    reasoning: str = Field(description="Brief explanation")

class CompanyFieldExtraction(BaseModel):
    name: Optional[str] = Field(description="Company name (cleaned)")
    city: Optional[str] = Field(description="City where company is located")
    country: Optional[str] = Field(description="Country where company is located")
    phone_number: Optional[str] = Field(description="Landline phone number (not mobile)")
    street_address: Optional[str] = Field(description="Full street address")

class TeamAnalysis(BaseModel):
    employee_count: int = Field(description="Number of individual people/names found on team page")
    confidence: float = Field(description="Confidence in the count (0.0-1.0)")
    names_found: list[str] = Field(description="List of individual names identified")

class RelevanceAndContact(BaseModel):
    is_relevant: bool = Field(description="True if architecture/engineering/interior design company")
    confidence: float = Field(description="Confidence score 0.0-1.0")
    reasoning: str = Field(description="Brief explanation for relevance classification")
    phone_number: Optional[str] = Field(description="Landline phone number found (avoid mobile numbers starting with 07)")
    street_address: Optional[str] = Field(description="Full street address found")

class TeamMemberCount(BaseModel):
    employee_count: int = Field(description="Number of individual people/names found")
    confidence: float = Field(description="Confidence in the count (0.0-1.0)")
    names_found: list[str] = Field(description="List of individual names identified")

def classify_relevance_and_contact(company_data):
    """(/gemini_classifier.classify_relevance_and_contact) - Classify relevance and extract contact info"""
    
    llm = ChatVertexAI(
        model="gemini-2.5-pro",
        temperature=0,
        project=os.getenv('GOOGLE_CLOUD_PROJECT')
    )
    
    parser = PydanticOutputParser(pydantic_object=RelevanceAndContact)
    
    prompt = PromptTemplate(
        template="""Analyze this company for relevance and extract contact information:

        1. RELEVANCE: Is this architecture/engineering/interior design?
        RELEVANT: 
        - Architecture firms, architectural services
        - Civil, structural, mechanical engineering (building-focused)  
        - Interior design services, space planning
        - PLANNING CONSULTANTS (urban planning, development planning)
        - DESIGN CONSULTANTS (architectural design consulting, engineering design consulting)
        - PROJECT MANAGEMENT for construction/architecture projects
        
        IRRELEVANT:
        - Software/technology companies
        - Manufacturing companies  
        - Cleaning, maintenance, or restoration services (even if building-related)
        - General business consulting (HR, finance, marketing)
        - Product suppliers or material vendors
        - Restaurants, retail, or other unrelated businesses
        
        2. CONTACT INFO: Extract landline phone and street address
        Look for: Office phone numbers (avoid mobile numbers starting with 07), full street addresses
        
        Company: {company_name}
        Website Content: {website_content}
        
        {format_instructions}""",
        input_variables=["company_name", "website_content"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # Smart content selection - About + Contact priority, Homepage as fallback
    website_content = ""
    has_about = bool(company_data.get('about_text'))
    has_contact = bool(company_data.get('contact_text'))
    
    # Always include About page if available
    if has_about:
        website_content += "=== ABOUT PAGE ===\n\n" + company_data['about_text']
    
    # Always include Contact page if available  
    if has_contact:
        website_content += "\n\n=== CONTACT PAGE ===\n\n" + company_data['contact_text']
    
    # Add Homepage only if missing About OR Contact
    if (not has_about or not has_contact) and company_data.get('homepage_text'):
        website_content += "\n\n=== HOMEPAGE ===\n\n" + company_data['homepage_text']
    
    chain = prompt | llm | parser
    result = chain.invoke({
        "company_name": company_data.get('company_name', ''),
        "website_content": website_content.strip()
    })
    
    return {
        'is_relevant': result.is_relevant,
        'confidence': result.confidence,
        'reasoning': result.reasoning,
        'phone_number': result.phone_number,
        'street_address': result.street_address
    }

def analyze_team_members(company_data):
    """(/gemini_classifier.analyze_team_members) - Count team members from team/about pages"""
    
    # Combine team and about page content
    team_content = ""
    if company_data.get('team_text'):
        team_content += "=== TEAM PAGE ===\n\n" + company_data['team_text']
    
    if company_data.get('about_text'):
        team_content += "\n\n=== ABOUT PAGE ===\n\n" + company_data['about_text']
    
    if not team_content.strip():
        return {'employee_count': 0, 'confidence': 0.0, 'names_found': []}
    
    llm = ChatVertexAI(
        model="gemini-2.5-pro",
        temperature=0,
        project=os.getenv('GOOGLE_CLOUD_PROJECT')
    )
    
    parser = PydanticOutputParser(pydantic_object=TeamMemberCount)
    
    prompt = PromptTemplate(
        template="""Count the individual people/employees mentioned in this content.

        Look carefully for:
        - Individual names (first name + last name combinations like "John Smith", "Sarah Johnson")
        - Staff bios or profiles with names
        - Team member listings with names
        - "Meet the team" sections with actual names
        - Director/Partner/Founder listings with real names
        - Employee photos with names
        
        Ignore:
        - Generic titles without names ("Managing Director", "Senior Architect")
        - Company names or department names
        - Client names or project names  
        - Repeated names (count each person only once)
        - Awards or certifications without personal names
        
        Count EVERY unique person mentioned by name. Be thorough.
        
        Content: {content}
        
        {format_instructions}""",
        input_variables=["content"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    result = chain.invoke({"content": team_content})
    
    return {
        'employee_count': result.employee_count,
        'confidence': result.confidence,
        'names_found': result.names_found
    }

# Keep original functions for backward compatibility with test_scraper.py
def classify_company_relevance(company_data):
    """(/gemini_classifier.classify_company_relevance) - Classify if company is relevant"""
    
    llm = ChatVertexAI(
        model="gemini-2.5-pro",
        temperature=0,
        project=os.getenv('GOOGLE_CLOUD_PROJECT')
    )
    
    parser = PydanticOutputParser(pydantic_object=CompanyClassification)
    
    prompt = PromptTemplate(
        template="""Analyze if this company is in architecture, engineering, or interior design.

        RELEVANT: 
        - Architecture firms, architectural services
        - Civil, structural, mechanical engineering (building-focused)
        - Interior design services, space planning
        - PLANNING CONSULTANTS (urban planning, development planning)
        - DESIGN CONSULTANTS (architectural design consulting, engineering design consulting)
        - PROJECT MANAGEMENT for construction/architecture projects
        
        IRRELEVANT: 
        - Software/technology companies 
        - Manufacturing companies
        - Cleaning, maintenance, or restoration services (even if building-related)
        - General business consulting (HR, finance, marketing)
        - Product suppliers or material vendors
        - Restaurants, retail, or other unrelated businesses
        
        Company: {company_name}
        Description: {business_description}
        
        {format_instructions}""",
        input_variables=["company_name", "business_description"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    result = chain.invoke({
        "company_name": company_data.get('company_name', ''),
        "business_description": company_data.get('business_description', '')
    })
    
    return {
        'is_relevant': result.is_relevant,
        'confidence': result.confidence,
        'reasoning': result.reasoning
    }

def extract_company_fields(company_data):
    """(/gemini_classifier.extract_company_fields) - Extract key company information"""
    
    llm = ChatVertexAI(
        model="gemini-2.5-pro",
        temperature=0,
        project=os.getenv('GOOGLE_CLOUD_PROJECT')
    )
    
    parser = PydanticOutputParser(pydantic_object=CompanyFieldExtraction)
    
    prompt = PromptTemplate(
        template="""Extract the following information about this company from their website content:

        Company: {company_name}
        Website Content: {website_content}
        
        Extract:
        - Company name (clean, official name)
        - City (where they're located)
        - Country (where they're located)  
        - Phone number (landline only, not mobile numbers - avoid numbers starting with 07)
        - Street address (full address if available)
        
        Look carefully through ALL the content for contact information, addresses, and location details.
        
        {format_instructions}""",
        input_variables=["company_name", "website_content"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    website_content = ""
    if company_data.get('homepage_text'):
        website_content += company_data['homepage_text']
    if company_data.get('about_text'):
        website_content += "\n\n--- ABOUT PAGE ---\n\n" + company_data['about_text']
    if company_data.get('team_text'):
        website_content += "\n\n--- TEAM PAGE ---\n\n" + company_data['team_text']
    if company_data.get('contact_text'):
        website_content += "\n\n--- CONTACT PAGE ---\n\n" + company_data['contact_text']
    
    chain = prompt | llm | parser
    result = chain.invoke({
        "company_name": company_data.get('company_name', ''),
        "website_content": website_content.strip()
    })
    
    return {
        'name': result.name,
        'city': result.city,
        'country': result.country,
        'phone_number': result.phone_number,
        'street_address': result.street_address
    }

def count_team_members(team_page_content, about_page_content=None):
    """(/gemini_classifier.count_team_members) - Count individual people on team/about pages"""
    
    combined_content = ""
    if team_page_content:
        combined_content += "TEAM PAGE:\n" + team_page_content
    if about_page_content:
        combined_content += "\n\nABOUT PAGE:\n" + about_page_content
        
    if not combined_content.strip():
        return {'employee_count': 0, 'confidence': 0.0, 'names_found': []}
    
    llm = ChatVertexAI(
        model="gemini-2.5-pro",
        temperature=0,
        project=os.getenv('GOOGLE_CLOUD_PROJECT')
    )
    
    parser = PydanticOutputParser(pydantic_object=TeamAnalysis)
    
    prompt = PromptTemplate(
        template="""Analyze this content and count the number of individual people/employees.

        Look for:
        - Individual names (first name + last name combinations)
        - Staff bios or profiles  
        - Team member listings
        - Employee photos with names
        - "Meet the team" sections
        - Director/Partner listings with actual names
        
        Ignore:
        - Generic titles without names ("Managing Director", "Senior Architect")
        - Company names or department names
        - Repeated names (count each person only once)
        - Client names or project names
        
        Content:
        {content}
        
        {format_instructions}""",
        input_variables=["content"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    result = chain.invoke({"content": combined_content})
    
    return {
        'employee_count': result.employee_count,
        'confidence': result.confidence,
        'names_found': result.names_found
    }