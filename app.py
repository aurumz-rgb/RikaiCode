import streamlit as st
import os
import gc
import time
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import markdown 
from datetime import datetime

st.set_page_config(
    page_title="RikaiCode",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from config import (
    SKIP_EXTENSIONS, MAX_LINES_INTERACTIVE_PREVIEW, 
    AI_AVAILABLE, apply_styles, load_logo, estimate_tokens
)


from processing import (
    process_uploaded_files, process_zip_file, 
    process_github_url, process_gitlab_url
)


from analysis import (
    get_file_stats, calculate_repo_quality_score, get_grade_from_score, 
    analyze_static_quality, build_full_tree, scan_dependencies, 
    extract_code_structure, scan_security_issues, scan_tech_debt,
    detect_infrastructure, count_entities, extract_python_function_code,
    get_zhipu_client, ai_analyze_architecture, ai_explain_code, 
    ai_project_synopsis, ai_review_file, ai_onboarding_guide,
    ai_complexity_analysis, ai_dependency_suggestions, ai_refactoring_ideas
)


from export import (
    create_txt_content, export_html, export_docx, export_pdf, 
    export_json, export_ai_response_docx, export_ai_response_pdf
)


apply_styles()


if 'files_data' not in st.session_state: st.session_state.files_data = {}
if 'repo_meta' not in st.session_state: st.session_state.repo_meta = {}
if 'pr_stats' not in st.session_state: st.session_state.pr_stats = {}
if 'search_term' not in st.session_state: st.session_state.search_term = ""


logo_data = load_logo()
if logo_data:
    st.markdown(f'<div class="logo-container"><img src="{logo_data}" class="logo-img"></div>', unsafe_allow_html=True)

st.markdown("""
<h1 style='text-align: center; margin-bottom: 0;'>
    Rikai<span style='color: #d3a0eb;'>Code.</span>
</h1>
<p style='text-align: center; font-size: 1.2rem; color: #a0a0a0; margin-bottom: 30px;'>
    Advanced Repository Flattener, Context Generator & Intelligent Grader
            
</p>
""", unsafe_allow_html=True)


st.markdown("### 🛠️ Input Source")
input_method = st.selectbox(
    "Select source type", 
    ["🌐 GitHub Repository URL", "🦊 GitLab Repository URL", "📁 Upload Files (Multi-Select)", "📦 Upload ZIP Folder (.zip)"],
    label_visibility="collapsed"
)


if 'prev_input_method' not in st.session_state:
    st.session_state.prev_input_method = input_method

if st.session_state.prev_input_method != input_method:
    st.session_state.files_data = {}
    st.session_state.repo_meta = {}
    st.session_state.pr_stats = {}
    st.session_state.prev_input_method = input_method
    gc.collect()

if input_method == "📁 Upload Files (Multi-Select)":
    uploaded_files = st.file_uploader("Drag and drop files", accept_multiple_files=True, key="file_uploader_widget")
    if uploaded_files:
        st.session_state.files_data = process_uploaded_files(uploaded_files)
        st.session_state.repo_meta = {} 
        st.session_state.pr_stats = {}

elif input_method == "📦 Upload ZIP Folder (.zip)":
    zip_file = st.file_uploader("Drag and drop ZIP", type=['zip'], key="zip_uploader_widget")
    if zip_file:
        st.session_state.files_data = process_zip_file(zip_file)
        st.session_state.repo_meta = {}
        st.session_state.pr_stats = {}

elif input_method == "🌐 GitHub Repository URL":
    url = st.text_input("Enter Public GitHub URL", placeholder="https://github.com/user/repo", key="github_url_input")
    if st.button("Fetch Repository", key="fetch_github_btn"):
        if url:
            print(f"\n[Rikai Code] 🔎 User searched GitHub URL: {url}\n", flush=True)
            st.session_state.files_data = {}
            st.session_state.repo_meta = {}
            st.session_state.pr_stats = {}
            gc.collect()
            
            with st.spinner("Loading Repository… Please wait while the architecture loads. ⏳"):
                files, meta, pr_stats = process_github_url(url)
                st.session_state.files_data = files
                st.session_state.repo_meta = meta
                st.session_state.pr_stats = pr_stats

elif input_method == "🦊 GitLab Repository URL":
    url = st.text_input("Enter Public GitLab URL", placeholder="https://gitlab.com/user/repo", key="gitlab_url_input")
    if st.button("Fetch Repository", key="fetch_gitlab_btn"):
        if url:
            print(f"\n[Rikai Code] 🔎 User searched GitLab URL: {url}\n", flush=True)
            st.session_state.files_data = {}
            st.session_state.repo_meta = {}
            st.session_state.pr_stats = {}
            gc.collect()
            
            with st.spinner("Loading GitLab repository… May take some time... ⏳"):
                files, meta, pr_stats = process_gitlab_url(url)
                st.session_state.files_data = files
                st.session_state.repo_meta = meta
                st.session_state.pr_stats = pr_stats


st.markdown(f"""
<div class="info-box">
    <p><strong>Note:</strong> Large repositories may take time to process. Please wait for the architecture to load.</p>
    <p><strong>Local Files:</strong> If uploading files/ZIPs manually, stats and grading will be estimated based on static analysis only.</p>
    <p><strong>Optimization:</strong> To reduce processing time, the following file types are excluded from content analysis but listed in architecture: <strong>{', '.join(SKIP_EXTENSIONS)}</strong>.</p>
</div>
""", unsafe_allow_html=True)


if st.session_state.files_data:
    files_data = st.session_state.files_data
    repo_meta = st.session_state.repo_meta
    pr_stats = st.session_state.pr_stats
    
    st.markdown("---")
    

    if repo_meta:
        st.markdown("### 🌐 Repository Insights")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("⭐ Stars", repo_meta.get('stars', 0), help="Total number of stars the repository has received.")
        c2.metric("🍴 Forks", repo_meta.get('forks', 0), help="Total number of forks created from this repository.")
        c3.metric("👀 Watchers", repo_meta.get('watchers', 0), help="Number of users watching the repository for updates.")
        c4.metric("💻 Language", repo_meta.get('language', 'N/A'), help="The primary programming language used in the repository.")
        
    
        st.markdown("####  Derived Metrics")
        dm1, dm2, dm3, dm4 = st.columns(4)
        
        
        fork_ratio = round(repo_meta.get('forks', 0) / repo_meta.get('stars', 1), 2) if repo_meta.get('stars', 0) > 0 else 0
        dm1.metric("🍴 Fork Ratio", f"{fork_ratio}", help="Forks per Star. High ratio implies high utility/reuse.")
        
  
        age = repo_meta.get('age_years', 'N/A')
        dm2.metric("📅 Repo Age", f"{age} years", help="Time since repository creation.")
        
     
        open_i = repo_meta.get('open_issues', 0)
        dm3.metric("❓ Open Issues", f"{open_i}", help="Count of open issues. Compare with activity to gauge maintenance load.")
        

        merge_rate = pr_stats.get('merge_rate', 0)
        dm4.metric("🔄 MR Merge Rate", f"{merge_rate:.0%}", help="Percentage of closed MRs/PRs that were merged. High rate = healthy contribution flow.")


        st.markdown("####  Merge/Pull Request Deep Dive")
        pc1, pc2, pc3, pc4 = st.columns(4)
        pc1.metric("Open MRs", pr_stats.get('open', 'N/A'), help="Requests currently open and awaiting review or merge.")
        pc2.metric("Merged MRs", pr_stats.get('merged', 'N/A'), help="Requests that have been successfully merged.")
        pc3.metric("Closed (Rejected)", pr_stats.get('closed_rejected', 'N/A'), help="Requests that were closed without being merged.")
        pc4.metric("📖 Total MRs", pr_stats.get('total_prs', 'N/A'), help="Total number of Merge/Pull Requests.")
        
        st.markdown("---")
        

        if 'commit_datetimes' in repo_meta and repo_meta['commit_datetimes']:
            st.markdown("####  ~ Commit Activity Heatmap (Time of Day)")
            

            heatmap_data = [[0] * 24 for _ in range(7)] 
            days_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
            
            for dt in repo_meta['commit_datetimes']:
       
                day_of_week = dt.weekday()
                hour = dt.hour
                heatmap_data[day_of_week][hour] += 1
                
            fig_heatmap = go.Figure(data=go.Heatmap(
                z=heatmap_data,
                x=[f"{h}:00" for h in range(24)],
                y=list(days_map.values()),
                colorscale='Viridis'
            ))
            fig_heatmap.update_layout(
                paper_bgcolor='#171717', plot_bgcolor='#171717', 
                font_color='#ededed', 
                xaxis_title="Hour of Day (UTC)",
                yaxis_title="Day of Week",
                height=300
            )
            st.plotly_chart(fig_heatmap, width="stretch")
            
        if 'commit_dates' in repo_meta and repo_meta['commit_dates']:
            st.markdown("#### ~ Recent Commit Frequency")
            df_commits = pd.DataFrame(repo_meta['commit_dates'], columns=['date'])
            df_commits['count'] = 1
            df_commits = df_commits.groupby('date').sum().reset_index()
            
            fig_commits = px.bar(df_commits, x='date', y='count', 
                                 labels={'date': 'Date', 'count': 'Commits'},
                                 color_discrete_sequence=['#d3a0eb'])
            fig_commits.update_layout(
                paper_bgcolor='#171717', plot_bgcolor='#171717', 
                font_color='#ededed', xaxis=dict(gridcolor='#333'), yaxis=dict(gridcolor='#333')
            )
            st.plotly_chart(fig_commits, width="stretch")
        st.markdown("---")


    stats, total_lines, total_size = get_file_stats(files_data)
    content_text = create_txt_content(files_data)
    token_est = estimate_tokens(content_text)
    

    if repo_meta:
        score, breakdown = calculate_repo_quality_score(repo_meta, repo_meta.get('commit_dates', []), pr_stats)
        grade, grade_desc = get_grade_from_score(score)
        
        col_grade, col_stats = st.columns([1, 3])
        
        with col_grade:
            st.markdown(f"""
            <div class="grade-box">
                <div style="font-size: 1.2rem; color: #ededed;">Repository Rank</div>
                <div class="grade-letter">{grade}</div>
                <div style="color: #a0a0a0;">{grade_desc}</div>
                <div class="grade-reason">
                    <strong>Score Breakdown:</strong><br>
                    • Popularity: {breakdown.get('Popularity', 'N/A')}<br>
                    • Activity: {breakdown.get('Activity', 'N/A')}<br>
                    • Maintenance: {breakdown.get('Maintenance', 'N/A')}<br>
                    • Community: {breakdown.get('Community', 'N/A')}<br>
                    • Stability: {breakdown.get('Stability', 'N/A')}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        score, breakdown = analyze_static_quality(files_data, total_lines)
        grade, grade_desc = get_grade_from_score(score)
        
        col_grade, col_stats = st.columns([1, 3])
        with col_grade:
            st.markdown(f"""
            <div class="grade-box">
                <div style="font-size: 1.2rem; color: #ededed;">Static Rank</div>
                <div class="grade-letter">{grade}</div>
                <div style="color: #a0a0a0;">{grade_desc}</div>
                <div class="grade-reason">
                    <strong>Score Breakdown:</strong><br>
                    • Documentation: {breakdown.get('Documentation', 'N/A')}<br>
                    • Structure: {breakdown.get('Structure', 'N/A')}<br>
                    • Best Practices: {breakdown.get('Best Practices', 'N/A')}<br>
                    • Scale: {breakdown.get('Scale', 'N/A')}<br>
                    • Stability: {breakdown.get('Stability', 'N/A')}
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_stats:
        st.markdown("### ⌨️ Code Statistics")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Files", len(files_data))
        m2.metric("Total Lines", f"{total_lines:,}")
        m3.metric("Characters", f"{total_size:,}")
        m4.metric("Est. Tokens", f"{token_est:,}", help="Approximation of total tokens (1 token ≈ 4 chars). Useful for LLM context limits.")
        m5.metric("Est. Size", f"{total_size/1024:.1f} KB", help="Total size of the concatenated text content in Kilobytes.")


    

    st.markdown("---")
    st.markdown("### ~ Code Frame")

    entity_counts = count_entities(files_data)

    ec1, ec2, ec3 = st.columns(3)
    ec1.metric(" Total Imports", entity_counts['imports'], help="Total import statements found in Python/JS files.")
    ec2.metric(" Total Classes", entity_counts['classes'], help="Total class definitions found.")
    ec3.metric(" Total Functions", entity_counts['functions'], help="Total function definitions found.")

    
    is_huge_repo = total_lines > MAX_LINES_INTERACTIVE_PREVIEW
    if is_huge_repo:
        st.warning(f"⚠️ **Large Repository Detected ({total_lines:,} lines).** Interactive preview disabled to prevent crash.")



    st.markdown("#### Detected Dependencies")
    with st.expander("View Dependencies", expanded=False):
        deps = scan_dependencies(files_data)
        if deps:
            deps_html = " ".join([f"<span class='dep-tag'>{d}</span>" for d in deps])
            st.markdown(deps_html, unsafe_allow_html=True)
        else:
            st.info("No external dependencies found in common files.")
            

    st.markdown("#### Infrastructure & Tooling")
    with st.expander("View Detected Stack", expanded=False):
        infra = detect_infrastructure(files_data)
        if infra:
            st.markdown("Detected components:")
            components_html = " ".join([f"<span class='dep-tag'>{comp}</span>" for comp in infra])
            st.markdown(components_html, unsafe_allow_html=True)
        else:
            st.info("No standard infrastructure files (Docker, K8s, CI) detected.")


    st.markdown("#### 🔒 Security Heuristics")
    with st.expander("View Security Scan Results", expanded=False):
        with st.spinner("Scanning for potential secrets..."):
            security_issues = scan_security_issues(files_data)
        
        if security_issues:
            st.warning(f"Found {len(security_issues)} potential security concerns:")
            for issue in security_issues:
                st.markdown(f"""
                <div class="security-alert">
                    <strong>File:</strong> {issue['file']}<br>
                    <strong>Issue:</strong> {issue['type']}<br>
                    <strong>Occurrences:</strong> {issue['count']}<br>
                    <strong>Lines:</strong> {issue['lines']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("No hardcoded secrets or API keys detected by heuristics.")
            



    st.markdown("####  Code Structure (Classes/Funcs)")
    with st.expander("View Structure", expanded=False):
        structure = extract_code_structure(files_data)
        if structure:
            for fname, items in structure.items():
                st.markdown(f"**{fname}**")
                if items['classes']:
                    classes_str = ", ".join(items['classes'])
                    st.markdown(f"▫️ Classes: `{classes_str}`")
                if items['functions']:
                    funcs_str = ", ".join(items['functions'])
                    st.markdown(f"▫️ Functions: `{funcs_str}`")
                st.markdown("---")
        else:
            st.info("No structure detected or files too large.")


    st.markdown("---")
    st.markdown("### 📉 File Distribution Analysis")
    

    color_seq = px.colors.qualitative.Vivid
    

    df = pd.DataFrame(list(stats.items()), columns=['Extension', 'Count'])
    
    col_treemap, col_pie = st.columns(2)
    
    with col_treemap:
        st.markdown("#### Treemap View")
        fig_tree = px.treemap(df, path=['Extension'], values='Count', 
                         color='Count', color_continuous_scale='Viridis')
        fig_tree.update_layout(
            paper_bgcolor='#171717', font_color='#ededed',
            plot_bgcolor='#171717', margin=dict(t=0, l=0, r=0, b=0)
        )
        st.plotly_chart(fig_tree, width="stretch")

    with col_pie:
        st.markdown("#### Distribution View")
        fig_pie = px.pie(df, values='Count', names='Extension', hole=0.4, color_discrete_sequence=color_seq)
        fig_pie.update_layout(
            paper_bgcolor='#171717', font_color='#ededed',
            plot_bgcolor='#171717', legend=dict(bgcolor='#171717', font=dict(color='#ededed'))
        )
        st.plotly_chart(fig_pie, width="stretch")


    st.markdown("---")
    st.markdown("### ~ Project Architecture")
    arch_str = build_full_tree(files_data)
    
    if len(arch_str.splitlines()) > 30:
        with st.expander("View Full Architecture Diagram", expanded=False):
            st.markdown(f'<div class="arch-box">{arch_str}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="arch-box">{arch_str}</div>', unsafe_allow_html=True)



    st.markdown("---")
    st.markdown("### 🤖 Rikai AI Analysis & Synopsis")
    
    client = get_zhipu_client()
    
    if not AI_AVAILABLE:
        st.error("⚠️ AI library not found. Please check requirements.txt.")
    elif not client:
        st.warning("⚠️ API KEY not found. AI features are disabled.")
        st.caption("IF running locally, enable Rikai AI by adding your API Key to a `.env` file")
    else:
   
        with st.expander("🛠️ Architecture Overview", expanded=False):
            if st.button("Analyze Architecture", key="btn_arch_ai"):
                with st.spinner("Rikai is analyzing the repository structure... This may take time..."):
                    analysis = ai_analyze_architecture(client, files_data)
                    st.session_state['ai_res_arch'] = analysis
            
            if 'ai_res_arch' in st.session_state:
                resp = st.session_state['ai_res_arch']
                st.markdown(f'<div class="ai-response-box">{markdown.markdown(resp)}</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("📥 Download Response as DOCX", export_ai_response_docx("Architecture Overview", resp), file_name="Rikai_Architecture.docx")
                with c2:
                    st.download_button("📥 Download Response as PDF", export_ai_response_pdf("Architecture Overview", resp), file_name="Rikai_Architecture.pdf")

      
        with st.expander("🛠️ Project Synopsis & Summary", expanded=False):
            if st.button("Generate Project Synopsis", key="btn_synopsis"):
                with st.spinner("Generating executive summary..."):
                    st.session_state['ai_res_synopsis'] = ai_project_synopsis(client, files_data)
            
            if 'ai_res_synopsis' in st.session_state:
                resp = st.session_state['ai_res_synopsis']
                st.markdown(f'<div class="ai-response-box">{markdown.markdown(resp)}</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("📥 Download Respnse as DOCX", export_ai_response_docx("Project Synopsis", resp), file_name="Rikai_Synopsis.docx")
                with c2:
                    st.download_button("📥 Download Response as PDF", export_ai_response_pdf("Project Synopsis", resp), file_name="Rikai_Synopsis.pdf")


        with st.expander("🛠️ Complexity & Maintainability", expanded=False):
            if st.button("Analyze Complexity", key="btn_complexity"):
                with st.spinner("Calculating complexity metrics..."):
                    st.session_state['ai_res_comp'] = ai_complexity_analysis(client, files_data)
            
            if 'ai_res_comp' in st.session_state:
                resp = st.session_state['ai_res_comp']
                st.markdown(f'<div class="ai-response-box">{markdown.markdown(resp)}</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("📥 Download Response as DOCX", export_ai_response_docx("Complexity Analysis", resp), file_name="Rikai_Complexity.docx")
                with c2:
                    st.download_button("📥 Download Response as PDF", export_ai_response_pdf("Complexity Analysis", resp), file_name="Rikai_Complexity.pdf")

        
        with st.expander("🛠️ Refactoring Suggestions", expanded=False):
            if st.button("Suggest Refactoring", key="btn_refac"):
                with st.spinner("Thinking about improvements..."):
                    st.session_state['ai_res_refac'] = ai_refactoring_ideas(client, files_data)
            
            if 'ai_res_refac' in st.session_state:
                resp = st.session_state['ai_res_refac']
                st.markdown(f'<div class="ai-response-box">{markdown.markdown(resp)}</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("📥 Download Response as DOCX", export_ai_response_docx("Refactoring Ideas", resp), file_name="Rikai_Refactoring.docx")
                with c2:
                    st.download_button("📥 Download Response as PDF", export_ai_response_pdf("Refactoring Ideas", resp), file_name="Rikai_Refactoring.pdf")


        with st.expander("🚀 Developer Onboarding Guide", expanded=False):
            if st.button("Create Onboarding Guide", key="btn_onboard"):
                with st.spinner("Creating setup instructions..."):
                    st.session_state['ai_res_onboard'] = ai_onboarding_guide(client, files_data, infra)
            
            if 'ai_res_onboard' in st.session_state:
                resp = st.session_state['ai_res_onboard']
                st.markdown(f'<div class="ai-response-box">{markdown.markdown(resp)}</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("📥 Download Response as DOCX", export_ai_response_docx("Onboarding Guide", resp), file_name="Rikai_Onboarding.docx")
                with c2:
                    st.download_button("📥 Download Response as PDF", export_ai_response_pdf("Onboarding Guide", resp), file_name="Rikai_Onboarding.pdf")

       
        with st.expander("📦 Dependency Insights", expanded=False):
            if st.button("Analyze Dependencies", key="btn_deps"):
                with st.spinner("Checking dependencies..."):
                    st.session_state['ai_res_deps'] = ai_dependency_suggestions(client, files_data)
            
            if 'ai_res_deps' in st.session_state:
                resp = st.session_state['ai_res_deps']
                st.markdown(f'<div class="ai-response-box">{markdown.markdown(resp)}</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("📥 Download Response as DOCX", export_ai_response_docx("Dependency Insights", resp), file_name="Rikai_Dependencies.docx")
                with c2:
                    st.download_button("📥 Download Response as PDF", export_ai_response_pdf("Dependency Insights", resp), file_name="Rikai_Dependencies.pdf")

    
        with st.expander("🛠️ Interactive Code Review", expanded=False):
            st.write("Select a file for a detailed AI code review.")
            reviewable_files = [f for f in files_data if files_data[f]] 
            selected_file_rev = st.selectbox("Select File", reviewable_files, key="sel_file_rev")
            
            if st.button("Review Selected File", key="btn_review"):
                if selected_file_rev:
                    code = files_data[selected_file_rev]
                    with st.spinner(f"Reviewing {selected_file_rev}..."):
                        st.session_state['ai_res_review'] = ai_review_file(client, selected_file_rev, code)
                        st.session_state['ai_res_review_name'] = selected_file_rev
            
            if 'ai_res_review' in st.session_state:
                resp = st.session_state['ai_res_review']
                fname = st.session_state.get('ai_res_review_name', 'File')
                st.markdown(f'<div class="ai-response-box">{markdown.markdown(resp)}</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("📥 Download Response as DOCX", export_ai_response_docx(f"Review: {fname}", resp), file_name=f"Rikai_Review_{fname}.docx")
                with c2:
                    st.download_button("📥 Download Response as PDF", export_ai_response_pdf(f"Review: {fname}", resp), file_name=f"Rikai_Review_{fname}.pdf")


        with st.expander("💡 Explain Python Functions", expanded=False):
            st.write("Select a Python function to get an explanation.")
            
            structure = extract_code_structure(files_data)
            all_funcs = []
            for fname, data in structure.items():
                for func in data['functions']:
                    all_funcs.append(f"{fname}::{func}")
            
            if all_funcs:
                selected_func_path = st.selectbox("Select Function", all_funcs, key="sel_func_ai")
                
                if st.button("Explain Function", key="btn_func_ai"):
                    if "::" in selected_func_path:
                        fname, func_name = selected_func_path.split("::")
                        content = files_data.get(fname, "")
                        
                        if content:
                            with st.spinner(f"Rikai is explaining {func_name}..."):
                                func_code = extract_python_function_code(content, func_name)
                                
                                if func_code:
                                    st.session_state['ai_res_func'] = ai_explain_code(client, func_code, func_name)
                                    st.session_state['ai_res_func_name'] = func_name
                                else:
                                    st.warning("Could not extract function code for analysis.")
            
            if 'ai_res_func' in st.session_state:
                resp = st.session_state['ai_res_func']
                fname = st.session_state.get('ai_res_func_name', 'Function')
                st.markdown(f'<div class="ai-response-box">{markdown.markdown(resp)}</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("📥 Download Response as DOCX", export_ai_response_docx(f"Explanation: {fname}", resp), file_name=f"Rikai_Expl_{fname}.docx")
                with c2:
                    st.download_button("📥 Download Response as PDF", export_ai_response_pdf(f"Explanation: {fname}", resp), file_name=f"Rikai_Expl_{fname}.pdf")
            elif not all_funcs:
                 st.info("No Python functions found to explain.")


  
    if not is_huge_repo:
        st.markdown("---")
        st.markdown("### 📂 Code Preview")
        
        def update_search(): st.session_state.search_term = st.session_state.search_input
        
      
        search_val = st.text_input(
            "Search files",
            value=st.session_state.search_term,
            key="search_input",
            on_change=update_search,
            placeholder="Enter a file name to search...",
            label_visibility="collapsed"
        )
        
        for filename, content in files_data.items():
            if st.session_state.search_term.lower() not in filename.lower():
                continue
                
            ext = filename.split('.')[-1]
            icon = "🐍" if ext == 'py' else "📜"
            lines_count = len(content.splitlines())
            
            header = f"{icon} **{filename}** ({lines_count} lines)"
            
   
            single_file_data = content.encode('utf-8')
            
            with st.expander(header):
                c_prev, c_dl = st.columns([4, 1])
                with c_prev:
                    st.code(content, language='python' if ext=='py' else 'javascript')
                with c_dl:
                    st.download_button(
                        label="Download",
                        data=single_file_data,
                        file_name=filename,
                        mime="text/plain",
                        key=f"dl_single_{filename}"
                    )


    st.markdown("---")
    st.markdown("### 🔗 Export Options")
    
  
    e1, e2, e3, e4, e5, e6, e7 = st.columns(7)
    
    e1.download_button("Export Text (.txt)", content_text, "RikaiCode.txt", "text/plain")
    e5.download_button("Export Markdown (.md)", f"```\n{arch_str}\n```\n\n" + content_text, "RikaiCode.md", "text/markdown")
    e2.download_button("Export JSON (.json)", export_json(files_data), "RikaiCode.json", "application/json")
    e3.download_button("Export HTML (.html)", export_html(files_data), "RikaiCode.html", "text/html")
    
    latex_content = f"\\documentclass{{article}}\\begin{{document}}\\begin{{verbatim}}{arch_str}\\end{{verbatim}}\\end{{document}}"
    e4.download_button("Export LaTeX (.tex)", latex_content, "RikaiCode.tex", "application/x-tex")
    
    if e6.button("Generate DOCX"):
        with st.spinner("Generating..."):
            docx_file = export_docx(files_data)
            e6.download_button("Download DOCX", docx_file, "RikaiCode.docx")

    if e7.button("Generate PDF"):
        with st.spinner("Generating..."):
            pdf_file = export_pdf(files_data)
            e7.download_button("Download PDF", pdf_file, "RikaiCode.pdf")


gc.collect()

st.markdown("""
<div class="footer-custom">
    <div style="flex: 1; text-align: left;"></div>
    <div style="flex: 1; text-align: center;">
        <a href="https://github.com/aurumz-rgb/RikaiCode" target="_blank" class="footer-link">© 2026 aurumz-rgb — AGPL 3.0 License</a>
    </div>
    <div style="flex: 1;"></div>
</div>
""", unsafe_allow_html=True)