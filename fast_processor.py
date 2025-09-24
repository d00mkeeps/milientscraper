# /fast_processor.py
import pandas as pd
from website_scraper import scrape_company_pages
from gemini_classifier import classify_relevance_and_contact, analyze_team_members
import os
import time
from datetime import datetime

def process_companies_fast(csv_file='sample-prospects.csv', batch_size=100, start_from=0):
    """(/fast_processor.process_companies_fast) - Optimized processing with targeted AI calls"""
    
    try:
        df = pd.read_csv(csv_file)
        print(f"📁 Loaded {len(df)} companies from {csv_file}")
        
        # Calculate actual batch end
        end_index = min(start_from + batch_size, len(df))
        actual_batch_size = end_index - start_from
        
        print(f"🚀 Processing companies {start_from + 1} to {end_index} ({actual_batch_size} companies)")
        
    except FileNotFoundError:
        print(f"❌ Error: {csv_file} not found")
        return
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return
    
    # Create results directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f'fast_results_{timestamp}'
    os.makedirs(results_dir, exist_ok=True)
    
    batch_companies = df.iloc[start_from:end_index]
    results = []
    
    print("\n" + "="*60)
    
    for idx, company in batch_companies.iterrows():
        processed_count = len(results) + 1
        company_name = company.get('Company name', 'Unknown')
        website_url = company.get('Website URL', '')
        
        print(f"\n[{processed_count}/{actual_batch_size}] 📊 Processing: {company_name}")
        print(f"🌐 Website: {website_url}")
        
        # Create base result with all original data
        result = {
            'Record ID': company.get('Record ID'),
            'Company name': company_name,
            'Type': company.get('Type'),
            'Sector': company.get('Sector'), 
            'Company Domain Name': company.get('Company Domain Name'),
            'Number of Employees': company.get('Number of Employees', 11),
            'City': company.get('City'),
            'Country': company.get('Country'),
            'Company owner': company.get('Company owner'),
            'Create Date': company.get('Create Date'),
            'Website URL': website_url,
            'Phone Number': company.get('Phone Number'),
            'Last Activity Date': company.get('Last Activity Date'),
            'Country/Region': company.get('Country/Region'),
            'Industry': company.get('Industry'),
            'Lifecycle Stage': company.get('Lifecycle Stage'),
            'Street Address': company.get('Street Address')
        }
        
        # Quick exit for obvious DQ case
        if not website_url:
            result.update({
                'Lifecycle Stage': 'other',
                'Company owner': 'no owner',
                'Sector': 'n/a',
                'Type': 'other'
            })
            results.append(result)
            print("  ❌ DQ: No website URL")
            continue
            
        # Scrape website
        print("  🕷️ Scraping website...")
        scraping_results = scrape_company_pages(website_url)
        
        if scraping_results['error']:
            result.update({
                'Lifecycle Stage': 'other',
                'Company owner': 'no owner', 
                'Sector': 'n/a',
                'Type': 'other'
            })
            results.append(result)
            print(f"  ❌ DQ: Scraping failed - {scraping_results['error']}")
            continue
            
        # Check what pages were scraped
        pages_found = []
        if scraping_results['homepage']: pages_found.append('homepage')
        if scraping_results['about_page']: pages_found.append('about')  
        if scraping_results['team_page']: pages_found.append('team')
        if scraping_results['contact_page']: pages_found.append('contact')
        print(f"  📄 Pages scraped: {', '.join(pages_found)}")
            
        # AI Call 1: Relevance + Contact Analysis
        print("  🤖 AI Call 1: Relevance + Contact analysis...")
        try:
            relevance_analysis = classify_relevance_and_contact({
                'company_name': company_name,
                'homepage_text': scraping_results['homepage']['text'] if scraping_results.get('homepage') else '',
                'about_text': scraping_results['about_page']['text'] if scraping_results.get('about_page') else '',
                'contact_text': scraping_results['contact_page']['text'] if scraping_results.get('contact_page') else ''
            })
            
            print(f"  🔍 Relevance: {relevance_analysis['is_relevant']} (confidence: {relevance_analysis['confidence']:.2f})")
            print(f"  🔍 Reasoning: {relevance_analysis['reasoning'][:100]}...")
            
            # Check for irrelevant companies
            if not relevance_analysis['is_relevant'] and relevance_analysis['confidence'] > 0.8:
                result.update({
                    'Lifecycle Stage': 'other',
                    'Company owner': 'no owner',
                    'Sector': 'n/a', 
                    'Type': 'other'
                })
                results.append(result)
                print(f"  ❌ DQ: Irrelevant company (confidence: {relevance_analysis['confidence']:.2f})")
                continue
                
        except Exception as e:
            print(f"  ⚠️ AI Call 1 error: {str(e)}")
            # Keep for manual review on AI errors
            results.append(result)
            print(f"  🤔 Kept for manual review due to AI error")
            continue
        
        # Check if we have team/about pages for team analysis
        has_team_data = bool(scraping_results.get('team_page')) or bool(scraping_results.get('about_page'))
        
        if not has_team_data:
            # No team data - manual review
            owner = result.get('Company owner', 'James')
            
            # Update with contact info from first AI call
            if relevance_analysis['phone_number']:
                result['Phone Number'] = relevance_analysis['phone_number']
                print(f"  📞 Found phone: {relevance_analysis['phone_number']}")
                
            if relevance_analysis['street_address']:
                result['Street Address'] = relevance_analysis['street_address']
                print(f"  🏠 Found address: {relevance_analysis['street_address'][:50]}...")
            
            results.append(result)
            print(f"  🤔 MANUAL REVIEW: No team/about pages found")
            print(f"      Can't determine team size - assigned to: {owner}")
            continue
        
        # AI Call 2: Team Analysis
        print("  🤖 AI Call 2: Team analysis...")
        try:
            team_analysis = analyze_team_members({
                'team_text': scraping_results['team_page']['text'] if scraping_results.get('team_page') else '',
                'about_text': scraping_results['about_page']['text'] if scraping_results.get('about_page') else ''
            })
            
            team_count = team_analysis['employee_count']
            print(f"  🔍 Team count: {team_count} people (confidence: {team_analysis['confidence']:.2f})")
            if team_analysis['names_found']:
                names_preview = ', '.join(team_analysis['names_found'][:3])
                if len(team_analysis['names_found']) > 3:
                    names_preview += f"... (+{len(team_analysis['names_found']) - 3} more)"
                print(f"  🔍 Names found: {names_preview}")
            
            # Apply team size rules
            if 1 <= team_count < 5:
                # DQ for small team
                result.update({
                    'Lifecycle Stage': 'other',
                    'Company owner': 'no owner',
                    'Sector': 'n/a',
                    'Type': 'other',
                    'Number of Employees': team_count
                })
                results.append(result)
                print(f"  ❌ DQ: Team too small ({team_count} people)")
                
            elif team_count == 0:
                # Team parsing failed - manual review
                owner = result.get('Company owner', 'James')
                
                # Update with contact info
                if relevance_analysis['phone_number']:
                    result['Phone Number'] = relevance_analysis['phone_number']
                    print(f"  📞 Found phone: {relevance_analysis['phone_number']}")
                    
                if relevance_analysis['street_address']:
                    result['Street Address'] = relevance_analysis['street_address']
                    print(f"  🏠 Found address: {relevance_analysis['street_address'][:50]}...")
                
                results.append(result)
                print(f"  🤔 MANUAL REVIEW: Team parsing failed (0 people found)")
                print(f"      Assigned to: {owner}")
                
            else:
                # Approve with owner assignment
                if team_count >= 100:
                    owner = 'Matt'
                elif team_count >= 16:
                    owner = 'Ellinor'
                else:
                    owner = 'James'
                
                # Update result with all enhancements
                result.update({
                    'Company owner': owner,
                    'Number of Employees': team_count
                })
                
                # Update contact info
                if relevance_analysis['phone_number']:
                    result['Phone Number'] = relevance_analysis['phone_number']
                    print(f"  📞 Found phone: {relevance_analysis['phone_number']}")
                    
                if relevance_analysis['street_address']:
                    result['Street Address'] = relevance_analysis['street_address']
                    print(f"  🏠 Found address: {relevance_analysis['street_address'][:50]}...")
                
                results.append(result)
                print(f"  ✅ APPROVED: {team_count} people → Owner: {owner}")
                
        except Exception as e:
            print(f"  ⚠️ AI Call 2 error: {str(e)}")
            # Keep for manual review on team analysis errors
            owner = result.get('Company owner', 'James')
            
            # Still update with contact info from first AI call
            if relevance_analysis['phone_number']:
                result['Phone Number'] = relevance_analysis['phone_number']
                print(f"  📞 Found phone: {relevance_analysis['phone_number']}")
                
            if relevance_analysis['street_address']:
                result['Street Address'] = relevance_analysis['street_address']
                print(f"  🏠 Found address: {relevance_analysis['street_address'][:50]}...")
            
            results.append(result)
            print(f"  🤔 MANUAL REVIEW: Team analysis failed → Owner: {owner}")
        
        # Save progress every 10 companies
        if processed_count % 10 == 0:
            temp_df = pd.DataFrame(results)
            temp_file = f"{results_dir}/progress_checkpoint_{processed_count}.csv"
            temp_df.to_csv(temp_file, index=False)
            print(f"\n  💾 Progress checkpoint saved: {processed_count}/{actual_batch_size} companies")
        
        print("-" * 40)
    
    # Save final results
    results_df = pd.DataFrame(results)
    
    # Save full results 
    full_file = f"{results_dir}/batch_{start_from}_{end_index}_full_results.csv"
    results_df.to_csv(full_file, index=False)
    
    # Save HubSpot-ready import (clean columns only)
    hubspot_columns = [
        'Record ID', 'Company name', 'Type', 'Sector', 'Company Domain Name',
        'Number of Employees', 'City', 'Country', 'Company owner', 'Create Date',
        'Website URL', 'Phone Number', 'Last Activity Date', 'Country/Region',
        'Industry', 'Lifecycle Stage', 'Street Address'
    ]
    hubspot_df = results_df[hubspot_columns]
    hubspot_file = f"{results_dir}/batch_{start_from}_{end_index}_hubspot_import.csv"
    hubspot_df.to_csv(hubspot_file, index=False)
    
    # Print final summary
    print("\n" + "="*60)
    print("📊 BATCH PROCESSING COMPLETE")
    print("="*60)
    
    total = len(results)
    approved = len([r for r in results if r.get('Lifecycle Stage') != 'other'])
    dq_no_website = len([r for r in results if not r.get('Website URL')])
    dq_broken = len([r for r in results if r.get('Lifecycle Stage') == 'other' and 'Scraping failed' in str(r)])
    dq_irrelevant = len([r for r in results if r.get('Lifecycle Stage') == 'other' and 'Irrelevant' in str(r)])
    dq_small_team = len([r for r in results if r.get('Lifecycle Stage') == 'other' and 'small' in str(r)])
    manual_review = approved  # All approved items need manual review for final sector assignment
    
    print(f"📈 SUMMARY STATISTICS:")
    print(f"  • Total processed: {total}")
    print(f"  • ✅ Approved (need manual review): {approved}")
    print(f"  • ❌ DQ - No website: {dq_no_website}")
    print(f"  • ❌ DQ - Broken website: {dq_broken}")  
    print(f"  • ❌ DQ - Irrelevant company: {dq_irrelevant}")
    print(f"  • ❌ DQ - Team too small: {dq_small_team}")
    print(f"  • ⏰ Time saved: ~{(total - approved) * 5} minutes of manual review")
    
    print(f"\n💾 FILES SAVED:")
    print(f"  📊 Full results: {full_file}")
    print(f"  🎯 HubSpot import: {hubspot_file}")
    
    success_rate = (approved / total * 100) if total > 0 else 0
    print(f"\n🎯 Success rate: {success_rate:.1f}% of companies kept for review")
    
    # AI call efficiency
    total_ai_calls = sum([
        1 if r.get('Lifecycle Stage') != 'other' or 'Irrelevant' in str(r) else 0  # All got AI call 1
        for r in results
    ])
    team_ai_calls = approved  # Only approved companies got team analysis
    print(f"🤖 AI Efficiency: {total_ai_calls + team_ai_calls} total AI calls for {total} companies")

if __name__ == "__main__":
    # Example usage:
    
    # Test with small batch first
    process_companies_fast('sample-prospects.csv', batch_size=300, start_from=0)