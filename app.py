import os
# High-priority: Install browser binaries on the cloud server
os.system("playwright install chromium")

import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
# New import for stealth
try:
    from playwright_stealth import stealth_sync
except ImportError:
    os.system("pip install playwright-stealth")
    from playwright_stealth import stealth_sync

st.set_page_config(page_title="Indeed Data Hub", page_icon="💼", layout="wide")
st.title("💼 Indeed BC Job Data Hub (Cloud Version)")

job_query = st.text_input("Search Jobs (e.g. Web Designer):", "Web Developer")

def scrape_full_data(query):
    with sync_playwright() as p:
        # 1. Launch Headless for Cloud
        browser = p.chromium.launch(headless=True)
        
        # 2. Set a realistic User Agent to look like a Mac
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # 3. Apply Stealth to hide automation fingerprints
        stealth_sync(page)
        
        url = f"https://ca.indeed.com/jobs?q={query.replace(' ', '+')}&l=British+Columbia"
        
        try:
            # Navigate and wait for content
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Check for immediate blocking
            if "hcaptcha" in page.content().lower() or "cloudflare" in page.content().lower():
                st.error("🛑 Blocked by Cloudflare/Captcha. Cloud servers are often restricted.")
                return pd.DataFrame()

            page.wait_for_selector(".job_seen_beacon", timeout=30000)
            
            cards = page.query_selector_all(".job_seen_beacon")
            jobs_data = []

            for i in range(min(len(cards), 15)): 
                try:
                    current_cards = page.query_selector_all(".job_seen_beacon")
                    card = current_cards[i]
                    
                    title = card.query_selector("h2.jobTitle").inner_text()
                    company = card.query_selector('[data-testid="company-name"]').inner_text()
                    
                    link_el = card.query_selector("h2.jobTitle a")
                    job_link = "https://ca.indeed.com" + link_el.get_attribute("href") if link_el else "N/A"
                    
                    # Interaction simulation
                    card.click()
                    page.wait_for_timeout(3000) # Give the side panel time to load
                    
                    description = "No description found"
                    desc_el = page.query_selector("#jobDescriptionText")
                    if desc_el:
                        description = desc_el.inner_text()
                    
                    jobs_data.append({
                        "Job Title": title,
                        "Company": company,
                        "Link": job_link,
                        "Full Description": description
                    })
                    st.write(f"✅ Extracted: {title}")
                except:
                    continue

            browser.close()
            return pd.DataFrame(jobs_data)
            
        except Exception as e:
            st.error(f"Error during scrape: {e}")
            browser.close()
            return pd.DataFrame()

if st.button("🚀 Fetch All Job Data"):
    with st.spinner("🔍 Hunting for jobs... this may take a minute."):
        results = scrape_full_data(job_query)
        
    if not results.empty:
        st.success(f"Successfully fetched {len(results)} jobs!")
        
        st.dataframe(
            results.drop(columns=["Full Description"]),
            column_config={
                "Link": st.column_config.LinkColumn("Job Link")
            },
            use_container_width=True
        )
        
        for index, row in results.iterrows():
            with st.expander(f"Read Full Description: {row['Job Title']}"):
                st.write(f"**Company:** {row['Company']}")
                st.markdown(f"[View Job on Indeed]({row['Link']})")
                st.markdown("---")
                st.text(row['Full Description'])

        csv = results.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Data as CSV", csv, "indeed_data.csv", "text/csv")
