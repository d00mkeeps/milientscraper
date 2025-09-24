# /hubspot_formatter.py
import pandas as pd
from datetime import datetime
import os
import sys

def format_for_hubspot(df):
    """(/hubspot_formatter.format_for_hubspot) - Format DataFrame for HubSpot compatibility"""
    
    # Make a copy to avoid modifying original
    formatted_df = df.copy()
    
    # 1. Fix Lifecycle Stage: 'other' -> 'Other'
    if 'Lifecycle Stage' in formatted_df.columns:
        other_count = len(formatted_df[formatted_df['Lifecycle Stage'] == 'other'])
        formatted_df['Lifecycle Stage'] = formatted_df['Lifecycle Stage'].replace('other', 'Other')
        if other_count > 0:
            print(f"  📋 Fixed {other_count} lifecycle stages: 'other' -> 'Other'")
    
    # 2. Fix Company Owner: 'no owner' -> 'No Owner'  
    if 'Company owner' in formatted_df.columns:
        no_owner_count = len(formatted_df[formatted_df['Company owner'] == 'no owner'])
        formatted_df['Company owner'] = formatted_df['Company owner'].replace('no owner', 'No Owner')
        if no_owner_count > 0:
            print(f"  👤 Fixed {no_owner_count} company owners: 'no owner' -> 'No Owner'")
    
    # 3. Set all dates to today at 12:01am
    today_1201am = datetime.now().replace(hour=0, minute=1, second=0, microsecond=0)
    standard_date = today_1201am.strftime('%Y-%m-%d %H:%M')
    
    date_columns = ['Create Date', 'Last Activity Date']
    
    for col in date_columns:
        if col in formatted_df.columns:
            # Count existing records
            total_records = len(formatted_df)
            
            # Set all dates to today at 12:01am
            formatted_df[col] = standard_date
            
            print(f"  📅 Set all {total_records} '{col}' values to {standard_date}")
    
    return formatted_df

def format_csv_file(input_file, output_file=None):
    """(/hubspot_formatter.format_csv_file) - Format existing CSV file for HubSpot"""
    
    try:
        print(f"📁 Loading {input_file}...")
        df = pd.read_csv(input_file)
        print(f"   Loaded {len(df)} records")
        
        print(f"\n🔧 Applying HubSpot formatting...")
        formatted_df = format_for_hubspot(df)
        
        # Generate output filename if not provided
        if output_file is None:
            base_name = os.path.splitext(input_file)[0]
            output_file = f"{base_name}_hubspot_ready.csv"
        
        # Save formatted file
        formatted_df.to_csv(output_file, index=False)
        print(f"\n💾 Saved HubSpot-ready file: {output_file}")
        
        # Summary
        total_records = len(formatted_df)
        dq_records = len(formatted_df[formatted_df.get('Lifecycle Stage') == 'Other'])
        approved_records = total_records - dq_records
        
        print(f"\n📊 SUMMARY:")
        print(f"  • Total records: {total_records}")
        print(f"  • Approved for review: {approved_records}")
        print(f"  • Disqualified: {dq_records}")
        print(f"  • Ready for HubSpot import!")
        
        return output_file
        
    except FileNotFoundError:
        print(f"❌ Error: File '{input_file}' not found")
        return None
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        return None

def show_usage():
    """Display usage instructions"""
    print("HubSpot CSV Formatter")
    print("====================")
    print("Usage: python hubspot_formatter.py <input_file.csv> [output_file.csv]")
    print("\nExamples:")
    print("  python hubspot_formatter.py cleaned_companies.csv")
    print("  python hubspot_formatter.py batch_results.csv my_hubspot_upload.csv")
    print("\nFormats:")
    print("  • 'other' -> 'Other' (Lifecycle Stage)")
    print("  • 'no owner' -> 'No Owner' (Company owner)")
    print("  • All dates -> Today at 00:01 (yyyy-mm-dd hh:mm format)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_usage()
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("HubSpot CSV Formatter")
    print("=" * 50)
    
    result = format_csv_file(input_file, output_file)
    
    if result:
        print(f"\n✅ Success! Your file is ready for HubSpot import.")
        print(f"📄 Upload: {result}")
    else:
        print(f"\n❌ Failed to process {input_file}")
        sys.exit(1)