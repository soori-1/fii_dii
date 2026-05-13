from playwright.sync_api import sync_playwright
import pandas as pd
import os

def main():
    new_data = []
    with sync_playwright() as p:
        # Use a standard Chrome User-Agent to prevent bot-blocking
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("Navigating to Trendlyne...")
        page.goto('https://trendlyne.com/macro-data/fii-dii/month/cash-month/', timeout=60000)

        # 1. THE FIX: Wait for the table to actually render on the screen
        try:
            print("Waiting for data table to load...")
            page.wait_for_selector('table tbody tr td:first-child a', timeout=15000)
        except Exception as e:
            print("Error: The table did not load in time. Trendlyne might be blocking the GitHub server.")
            page.screenshot(path="debug_error.png")
            print("Saved screenshot to 'debug_error.png' to see what the bot is seeing.")
            browser.close()
            return

        # Gather month links
        month_links = page.evaluate('''() => {
            const rows = Array.from(document.querySelectorAll('table tbody tr td:first-child a'));
            return rows.map(a => ({ text: a.innerText.trim(), href: a.href }));
        }''')

        # Check if we got links
        if not month_links:
            print("Failed to extract links even after waiting.")
            browser.close()
            return

        # 2. Only scrape the FIRST link (The Current Month)
        latest_month = month_links[0]
        print(f"Scraping latest month: {latest_month['text']}")
        
        page.goto(latest_month['href'], timeout=60000)

        # Wait for the Cash Provisional tab to be ready
        try:
            page.wait_for_selector('text="Cash Provisional"', timeout=10000)
            cash_tab = page.locator('text="Cash Provisional"').first
            if cash_tab.is_visible():
                cash_tab.click()
                page.wait_for_timeout(2000) # Give it 2 seconds to switch tabs
        except Exception as e:
            print("Could not find or click the 'Cash Provisional' tab.")

        # Extract data exactly matching your CSV headers
        daily_data = page.evaluate('''() => {
            const rows = Array.from(document.querySelectorAll('table tbody tr'));
            return rows.map(row => {
                const cols = Array.from(row.querySelectorAll('td'));
                if (cols.length < 7) return null;
                return {
                    DATE: cols[0]?.innerText.trim(),
                    FII_Net_Purchase_Sales: cols[3]?.innerText.trim(),
                    DII_Net_Purchase_Sales: cols[4]?.innerText.trim()
                };
            }).filter(row => row && row.DATE && row.DATE !== 'Date');
        }''')
        
        new_data.extend(daily_data)
        browser.close()

    if not new_data:
        print("No data extracted from the current month's page.")
        return

    # 3. MERGE WITH YOUR EXISTING CSV
    csv_file = 'FII_DII_Daily_Data_2014_to_Today.csv'
    df_new = pd.DataFrame(new_data)
    
    if os.path.exists(csv_file):
        print("Found existing history. Merging new data...")
        df_old = pd.read_csv(csv_file, encoding='utf-8-sig')
        
        # Combine old and new data
        df_combined = pd.concat([df_new, df_old])
        
        # Standardize dates to find exact matches
        df_combined['DATE_PARSED'] = pd.to_datetime(df_combined['DATE'], errors='coerce')
        df_combined = df_combined.dropna(subset=['DATE_PARSED'])
        
        # Drop duplicates (keeps the freshly scraped data if dates overlap)
        df_combined = df_combined.sort_values('DATE_PARSED', ascending=False).drop_duplicates(subset=['DATE_PARSED'], keep='first')
        
        # Recalculate Total_Net for the new rows
        fii = pd.to_numeric(df_combined['FII_Net_Purchase_Sales'].astype(str).str.replace(',', ''), errors='coerce')
        dii = pd.to_numeric(df_combined['DII_Net_Purchase_Sales'].astype(str).str.replace(',', ''), errors='coerce')
        df_combined['Total_Net'] = fii + dii

        # Clean up and save
        df_combined = df_combined.drop(columns=['DATE_PARSED'])
        df_combined.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print("Successfully merged and saved.")
    else:
        print("CSV not found. Creating a new one...")
        # For a brand new file, calculate the total net
        df_new['Total_Net'] = pd.to_numeric(df_new['FII_Net_Purchase_Sales'].astype(str).str.replace(',', ''), errors='coerce') + pd.to_numeric(df_new['DII_Net_Purchase_Sales'].astype(str).str.replace(',', ''), errors='coerce')
        df_new.to_csv(csv_file, index=False, encoding='utf-8-sig')

if __name__ == "__main__":
    main()
