import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import os

st.set_page_config(page_title="Indeed Data Hub", page_icon="💼")
st.title("💼 Indeed BC Job Data Hub")

job_query = st.text_input("Search Jobs (e.g. Web Designer):", "Web Developer")

def scrape_full_data(query):
    # Setup persistent session to avoid verification loops
    user_data_dir = os.path.join(os.getcwd(), "browser_session")
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"] # Mask bot signatures
        )
        page = context.pages[0]
        page.goto(f"https://ca.indeed.com/jobs?q={query.replace(' ', '+')}&l=British+Columbia")
        
        st.warning("⚠️ Solve the human verification in the browser window!")
        page.wait_for_selector(".job_seen_beacon", timeout=60000)
        
        cards = page.query_selector_all(".job_seen_beacon")
        jobs_data = []

        # Scrape top 15 listings
        for i in range(min(len(cards), 15)): 
            try:
                current_cards = page.query_selector_all(".job_seen_beacon")
                card = current_cards[i]
                
                # 1. Capture Header Data
                title = card.query_selector("h2.jobTitle").inner_text()
                company = card.query_selector('[data-testid="company-name"]').inner_text()
                
                link_el = card.query_selector("h2.jobTitle a")
                job_link = "https://ca.indeed.com" + link_el.get_attribute("href") if link_el else "N/A"
                
                # 2. Click to load the side panel for the full text
                card.click()
                page.wait_for_timeout(2500) 
                
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

        context.close()
        return pd.DataFrame(jobs_data)

if st.button("🚀 Fetch All Job Data"):
    results = scrape_full_data(job_query)
    if not results.empty:
        st.success(f"Successfully fetched {len(results)} jobs!")
        
        # Display the table with the Link column
        # We hide the Description from the main table so it stays clean
        st.dataframe(
            results.drop(columns=["Full Description"]),
            column_config={
                "Link": st.column_config.LinkColumn("Job Link")
            },
            use_container_width=True
        )
        
        # Expanders to read the full descriptions individually
        for index, row in results.iterrows():
            with st.expander(f"Read Full Description: {row['Job Title']}"):
                st.write(f"**Company:** {row['Company']}")
                st.markdown("---")
                st.text(row['Full Description'])

        # CSV Download
        csv = results.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Data as CSV", csv, "indeed_data.csv", "text/csv")