# /test_scraper.py
import pandas as pd
from website_scraper import scrape_company_pages
from gemini_classifier import classify_company_relevance, extract_company_fields, count_team_members
import os

def test_sample_companies():
    """(/test_scraper.test_sample_companies) - Test scraping + AI classification + team counting + field extraction"""
    
    # Read the CSV file
    try:
        df = pd.read_csv('sample-prospects.csv')
        print(f"Loaded {len(df)} companies from CSV")
        print(f"Columns: {list(df.columns)}")
        print("\n" + "="*50)
        
    except FileNotFoundError:
        print("Error: sample-prospects.csv not found in root directory")
        return
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
    
    # Create results directory
    os.makedirs('test_results', exist_ok=True)
    
    # Test all 10 companies
    test_companies = df.head(10)
    
    results = []
    
    for idx, company in test_companies.iterrows():
        company_name = company.get('Company name', 'Unknown')
        website_url = company.get('Website URL', '')
        
        print(f"\n📊 Testing: {company_name}")
        print(f"🌐 Website: {website_url}")
        print("-" * 40)
        
        if not website_url:
            print("❌ No website URL found")
            results.append({
                'company': company_name,
                'website': website_url,
                'scraping_success': False,
                'error': 'No website URL',
                'ai_classification': None,
                'team_analysis': None,
                'extracted_fields': None,
                'final_recommendation': 'DQ - No website'
            })
            continue
            
        # Step 1: Scrape the company
        scraping_results = scrape_company_pages(website_url)
        
        if scraping_results['error']:
            print(f"❌ Scraping Error: {scraping_results['error']}")
            results.append({
                'company': company_name,
                'website': website_url,
                'scraping_success': False,
                'error': scraping_results['error'],
                'ai_classification': None,
                'team_analysis': None,
                'extracted_fields': None,
                'final_recommendation': 'DQ - Broken website'
            })
            continue
        else:
            print("✅ Scraping successful!")
            
            if scraping_results['business_description']:
                print(f"📝 Business: {scraping_results['business_description'][:200]}...")
                
            pages_found = []
            if scraping_results['homepage']: pages_found.append('homepage')
            if scraping_results['about_page']: pages_found.append('about')  
            if scraping_results['team_page']: pages_found.append('team')
            if scraping_results['contact_page']: pages_found.append('contact')  # NEW
            print(f"📄 Pages scraped: {', '.join(pages_found)}")
        
        # Step 2: Team Member Analysis (if team page exists)
        team_analysis = None
        if scraping_results.get('team_page'):
            try:
                team_analysis = count_team_members(scraping_results['team_page']['text'])
                print(f"\n👥 Team Analysis:")
                print(f"   People found: {team_analysis['employee_count']}")
                print(f"   Confidence: {team_analysis['confidence']:.2f}")
                if team_analysis['names_found']:
                    print(f"   Names: {', '.join(team_analysis['names_found'][:5])}{'...' if len(team_analysis['names_found']) > 5 else ''}")
                
                # Check for team size DQ
                if team_analysis['employee_count'] < 5:
                    print(f"❌ DQ: Team too small ({team_analysis['employee_count']} people)")
                    results.append({
                        'company': company_name,
                        'website': website_url,
                        'scraping_success': True,
                        'team_analysis': team_analysis,
                        'ai_classification': None,
                        'extracted_fields': None,
                        'final_recommendation': f"DQ - Too few employees ({team_analysis['employee_count']} people)"
                    })
                    print("\n" + "="*60)
                    continue
                    
            except Exception as e:
                print(f"❌ Team Analysis Error: {str(e)}")
                team_analysis = {'error': str(e)}
        else:
            print("\n👥 No team page found")
        
        # Step 3: AI Classification
        try:
            classification = classify_company_relevance({
                'company_name': company_name,
                'business_description': scraping_results.get('business_description', '')
            })
            
            print(f"\n🤖 AI Classification: {'RELEVANT' if classification['is_relevant'] else 'IRRELEVANT'}")
            print(f"📊 Confidence: {classification['confidence']:.2f}")
            print(f"💭 Reasoning: {classification['reasoning']}")
            
        except Exception as e:
            print(f"❌ AI Classification Error: {str(e)}")
            classification = {
                'is_relevant': None,
                'confidence': 0.0,
                'reasoning': f'Classification error: {str(e)}'
            }
        
        # Step 4: Field Extraction (only if relevant or uncertain)
        extracted_fields = None
        if classification.get('is_relevant') != False:  # True or None (error)
            try:
                extracted_fields = extract_company_fields({
                    'company_name': company_name,
                    'homepage_text': scraping_results['homepage']['text'] if scraping_results.get('homepage') else '',
                    'about_text': scraping_results['about_page']['text'] if scraping_results.get('about_page') else '',
                    'team_text': scraping_results['team_page']['text'] if scraping_results.get('team_page') else '',
                    'contact_text': scraping_results['contact_page']['text'] if scraping_results.get('contact_page') else ''  # NEW
                })
                
                print(f"\n📋 Extracted Fields:")
                print(f"   Name: {extracted_fields.get('name', 'Not found')}")
                print(f"   City: {extracted_fields.get('city', 'Not found')}")
                print(f"   Country: {extracted_fields.get('country', 'Not found')}")
                print(f"   Phone: {extracted_fields.get('phone_number', 'Not found')}")
                print(f"   Address: {extracted_fields.get('street_address', 'Not found')}")
                
            except Exception as e:
                print(f"❌ Field Extraction Error: {str(e)}")
                extracted_fields = {'error': str(e)}
        
        # Step 5: Determine final recommendation
        if classification['is_relevant'] == False and classification['confidence'] > 0.8:
            final_recommendation = f"DQ - AI confident irrelevant ({classification['confidence']:.2f})"
        else:
            final_recommendation = "Keep for human review"
            
        print(f"🎯 Final Recommendation: {final_recommendation}")
        
        results.append({
            'company': company_name,
            'website': website_url,
            'scraping_success': True,
            'has_description': bool(scraping_results.get('business_description')),
            'team_analysis': team_analysis,
            'ai_relevant': classification.get('is_relevant'),
            'ai_confidence': classification.get('confidence', 0.0),
            'ai_reasoning': classification.get('reasoning', ''),
            'extracted_fields': extracted_fields,
            'final_recommendation': final_recommendation,
            'error': None
        })
        
        print("\n" + "="*60)
    
    # Save detailed results with better formatting
    with open('test_results/scraping_results.txt', 'w') as f:
        f.write("WEBSITE SCRAPING + AI CLASSIFICATION + TEAM ANALYSIS + FIELD EXTRACTION\n")
        f.write("="*80 + "\n\n")
        
        for result in results:
            f.write(f"Company: {result['company']}\n")
            f.write(f"Website: {result['website']}\n")
            f.write(f"Scraping Success: {result['scraping_success']}\n")
            
            if result['scraping_success']:
                f.write(f"Business Description Found: {result['has_description']}\n")
                
                # Team analysis
                if result['team_analysis'] and not result['team_analysis'].get('error'):
                    f.write(f"Team Members Found: {result['team_analysis']['employee_count']}\n")
                    f.write(f"Team Analysis Confidence: {result['team_analysis']['confidence']}\n")
                    if result['team_analysis']['names_found']:
                        f.write(f"Names Found: {', '.join(result['team_analysis']['names_found'])}\n")
                elif result['team_analysis'] and result['team_analysis'].get('error'):
                    f.write(f"Team Analysis Error: {result['team_analysis']['error']}\n")
                else:
                    f.write("No team page found\n")
                
                # AI classification
                f.write(f"AI Relevant: {result['ai_relevant']}\n")
                f.write(f"AI Confidence: {result['ai_confidence']}\n")
                f.write(f"AI Reasoning: {result['ai_reasoning']}\n")
                
                # Field extraction
                if result['extracted_fields'] and not result['extracted_fields'].get('error'):
                    f.write(f"Extracted Name: {result['extracted_fields'].get('name', 'Not found')}\n")
                    f.write(f"Extracted City: {result['extracted_fields'].get('city', 'Not found')}\n")
                    f.write(f"Extracted Country: {result['extracted_fields'].get('country', 'Not found')}\n")
                    f.write(f"Extracted Phone: {result['extracted_fields'].get('phone_number', 'Not found')}\n")
                    f.write(f"Extracted Address: {result['extracted_fields'].get('street_address', 'Not found')}\n")
                elif result['extracted_fields'] and result['extracted_fields'].get('error'):
                    f.write(f"Field Extraction Error: {result['extracted_fields']['error']}\n")
            
            f.write(f"Final Recommendation: {result['final_recommendation']}\n")
            f.write(f"Error: {result['error']}\n")
            f.write("-" * 50 + "\n\n")
    
    print(f"\n💾 Detailed results saved to test_results/scraping_results.txt")
    
    # Summary statistics
    total = len(results)
    successful_scrapes = len([r for r in results if r['scraping_success']])
    dq_broken_sites = len([r for r in results if 'Broken website' in r['final_recommendation']])
    dq_team_size = len([r for r in results if 'Too few employees' in r['final_recommendation']])
    dq_ai_irrelevant = len([r for r in results if 'AI confident irrelevant' in r['final_recommendation']])
    keep_for_review = len([r for r in results if 'Keep for human review' in r['final_recommendation']])
    successful_extractions = len([r for r in results if r.get('extracted_fields') and not r['extracted_fields'].get('error')])
    successful_team_analysis = len([r for r in results if r.get('team_analysis') and not r['team_analysis'].get('error')])
    
    print(f"\n📊 SUMMARY:")
    print(f"• Total companies: {total}")
    print(f"• Successful scrapes: {successful_scrapes}/{total}")
    print(f"• Successful team analysis: {successful_team_analysis}/{successful_scrapes}")
    print(f"• Successful field extractions: {successful_extractions}/{successful_scrapes}")
    print(f"• DQ - Broken websites: {dq_broken_sites}")
    print(f"• DQ - Team too small: {dq_team_size}")
    print(f"• DQ - AI irrelevant: {dq_ai_irrelevant}")
    print(f"• Keep for human review: {keep_for_review}")
    
    total_dq = dq_broken_sites + dq_team_size + dq_ai_irrelevant
    print(f"• Total time saved: ~{total_dq * 5} minutes of human review")

if __name__ == "__main__":
    test_sample_companies()