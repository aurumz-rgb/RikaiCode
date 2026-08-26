import os
import re
import json
import math
from datetime import datetime, timedelta
from collections import Counter


from config import AI_AVAILABLE, LOGO_PATH


try:
    from zai import ZaiClient
except ImportError:
    pass


def get_file_stats(files_dict):
    ext_counts = {}
    total_lines = 0
    total_size = 0
    for name, content in files_dict.items():
        ext = name.split('.')[-1] if '.' in name else 'folder/other'
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
        lines = len(content.splitlines())
        total_lines += lines
        total_size += len(content)
    return ext_counts, total_lines, total_size

import math

def calculate_repo_quality_score(meta, commits, pr_stats):
    """
    Quality-focused Grading Logic.
    Shifts weight away from raw star/fork numbers towards maintenance, activity, and PR health.
    Returns (score, breakdown_dict)
    """
    score = 0
    breakdown = {}

    # ---- 1. Popularity (15 pts)
    stars = meta.get('stars', 0)
    forks = meta.get('forks', 0)
    
    
    star_pts = round(min(10, 10 * (math.log10(stars + 1) / math.log10(2000 + 1))), 2) if stars > 0 else 0
  
    fork_pts = round(min(5, 5 * (math.log10(forks + 1) / math.log10(200 + 1))), 2) if forks > 0 else 0
    
    popularity_score = round(star_pts + fork_pts, 2)
    score += popularity_score
    breakdown['Popularity'] = f"{popularity_score}/15 (Stars: {star_pts}, Forks: {fork_pts})"

    # ---- 2. Activity (30 pts) 
    recency_pts = 0.0
    last_commit_str = meta.get('pushed_at', None)
    days_diff = 999
    if last_commit_str:
        try:
            clean_date = last_commit_str.replace('Z', '+00:00')
            last_date = datetime.fromisoformat(clean_date)
            now = datetime.now(last_date.tzinfo)
            days_diff = (now - last_date).days
           
            recency_pts = round(15 * math.exp(-days_diff / 270), 2)
        except: pass

    # Commit frequency (15 pts) 
    commit_count = len(commits)
    if commit_count > 100: freq_pts = 15.0
    elif commit_count > 50: freq_pts = 12.0
    elif commit_count > 20: freq_pts = 9.0
    elif commit_count > 5: freq_pts = 6.0
    else: freq_pts = 3.0

    activity_score = round(recency_pts + freq_pts, 2)
    score += activity_score
    breakdown['Activity'] = f"{activity_score}/30 (Recency: {recency_pts} (last push {days_diff}d ago), Freq: {freq_pts})"

    # ---- 3. Maintenance (35 pts) 
    open_issues = meta.get('open_issues', 0)
    stars_safe = max(stars, 1)
    
    # Issue Health (15 pts) 
    if open_issues == 0: issue_pts = 15.0
    elif open_issues < 50: issue_pts = 13.0
    elif open_issues < 200: issue_pts = 11.0
    else:
        issue_density = open_issues / stars_safe
        if issue_density > 1.0: issue_pts = 6.0  
        else: issue_pts = 9.0

    # PR Health (20 pts) 
    pr_merge_rate = pr_stats.get('merge_rate', 0)
    total_prs = pr_stats.get('total_prs', 0)
    if total_prs == 0:
        pr_pts = 12.0  
    elif pr_merge_rate > 0.6:
        pr_pts = 20.0
    elif pr_merge_rate > 0.3:
        pr_pts = 16.0
    else:
        pr_pts = 8.0

    maint_score = round(issue_pts + pr_pts, 2)
    score += maint_score
    breakdown['Maintenance'] = f"{maint_score}/35 (Issue Health: {issue_pts}, PR Health: {pr_pts})"

    # ---- 4. Community (10 pts) 
    watchers = meta.get('watchers', 0)
    comm_pts = round(min(10, 10 * (math.log10(watchers + 1) / math.log10(200 + 1))), 2) if watchers > 0 else 0
    score += comm_pts
    breakdown['Community'] = f"{comm_pts}/10 (Watchers: {watchers})"

    # ---- 5. Stability (10 pts) 
    if meta.get('archived', False):
        stab_pts = 0.0
    else:
        stab_pts = 10.0
    score += stab_pts
    breakdown['Stability'] = f"{stab_pts}/10 (Archived: {meta.get('archived', False)})"

    final_score = round(min(100, max(0, score)), 2)
    return final_score, breakdown

def get_grade_from_score(score):
   
    if score >= 95:
        return 'A++', "Exceptional - top-tier project with outstanding metrics across every dimension."
    elif score >= 90:
        return 'A+', "Excellent - strong, well-maintained, and trusted by the community."
    elif score >= 85:
        return 'A', "Great - reliable, active, and follows best practices."
    elif score >= 80:
        return 'A-', "Very good - solid project with minor gaps."
    elif score >= 75:
        return 'B+', "Good - generally healthy but room for improvement."
    elif score >= 70:
        return 'B', "Above average - usable but verify specific metrics."
    elif score >= 65:
        return 'B-', "Fair - functional with notable weaknesses."
    elif score >= 60:
        return 'C+', "Average - review maintenance and activity carefully."
    elif score >= 50:
        return 'C', "Below average - possible stagnation or quality concerns."
    elif score >= 40:
        return 'D', "Weak - likely unmaintained or poorly structured."
    else:
        return 'F', "Poor - high risk; do not use without significant review."

def analyze_static_quality(files_dict, total_lines):
    """
    Quality-focused Static Grading Logic.
    Much more forgiving on file size and comments, rewards basic best practices heavily.
    Returns (score, breakdown_dict)
    """
    score = 0
    breakdown = {}

    # ---- 1. Documentation (25 pts) 
    readme_pts = 0.0
    readme_content = ""
    for f in files_dict:
        if 'readme' in f.lower():
            readme_content = files_dict[f]
            break
            
    if readme_content:
        readme_pts = 10.0  
        if len(readme_content) > 500: readme_pts = 12.0
        if len(readme_content) > 2000: readme_pts = 15.0

    # Comments (10 pts) 
    total_comments = 0
    for content in files_dict.values():
        total_comments += len(re.findall(r'#.*|//.*|/\*.*?\*/', content, re.DOTALL))
    doc_ratio = total_comments / total_lines if total_lines > 0 else 0
    
    if doc_ratio > 0.05: comment_pts = 10.0
    elif doc_ratio > 0.02: comment_pts = 7.0
    elif doc_ratio > 0.0: comment_pts = 4.0
    else: comment_pts = 0.0

    doc_score = round(readme_pts + comment_pts, 2)
    score += doc_score
    breakdown['Documentation'] = f"{doc_score}/25 (Readme: {readme_pts}, Comments: {comment_pts})"

    # ---- 2. Structure (25 pts) 
    file_count = max(len(files_dict), 1)
    avg_lines = total_lines / file_count
    
    
    if avg_lines < 400: mod_pts = 15.0
    elif avg_lines < 800: mod_pts = 10.0
    elif avg_lines < 1500: mod_pts = 5.0
    else: mod_pts = 2.0

    # Organization (10 pts)
    org_pts = 0.0
    has_entry = any('main' in f.lower() or 'app' in f.lower() or 'index' in f.lower() for f in files_dict.keys())
    has_folders = any('/' in f for f in files_dict.keys())
    if has_entry: org_pts += 5.0
    if has_folders: org_pts += 5.0

    struct_score = round(mod_pts + org_pts, 2)
    score += struct_score
    breakdown['Structure'] = f"{struct_score}/25 (Modularity: {mod_pts} (avg {avg_lines:.0f} L/file), Org: {org_pts})"

    # ---- 3. Best Practices (25 pts) 
    dep_files = ['requirements.txt', 'package.json', 'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle', 'Gemfile', 'composer.json']
    has_deps = any(d in files_dict for d in dep_files)
    has_gitignore = any('.gitignore' in f for f in files_dict.keys())
    has_license = any('license' in f.lower() for f in files_dict.keys())
    has_ci = any(k in f for f in files_dict.keys() for k in ['.github/workflows/', '.gitlab-ci.yml', 'Jenkinsfile', 'azure-pipelines.yml'])

    bp_score = 0.0
    if has_deps: bp_score += 10.0
    if has_gitignore: bp_score += 5.0
    if has_license: bp_score += 5.0
    if has_ci: bp_score += 5.0
    bp_score = round(bp_score, 2)
    score += bp_score
    breakdown['Best Practices'] = f"{bp_score}/25 (Deps: {has_deps}, Gitignore: {has_gitignore}, License: {has_license}, CI: {has_ci})"

    # ---- 4. Scale (15 pts) 
    if total_lines > 1000: scale_pts = 15.0
    elif total_lines > 200: scale_pts = 10.0
    else: scale_pts = 5.0
    score += scale_pts
    breakdown['Scale'] = f"{scale_pts}/15 (Lines: {total_lines})"

    # ---- 5. Stability (10 pts) 
    if len(files_dict) >= 5: stab_pts = 10.0
    elif len(files_dict) >= 2: stab_pts = 7.0
    else: stab_pts = 4.0
    score += stab_pts
    breakdown['Stability'] = f"{stab_pts}/10 (File Count: {len(files_dict)})"

    final_score = round(min(100, max(0, score)), 2)
    return final_score, breakdown

def build_full_tree(files_dict):
    lines = ["PROJECT ARCHITECTURE", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
    sorted_files = sorted(files_dict.keys())
    has_main = any('main' in f.lower() or 'app' in f.lower() for f in sorted_files)
    
    lines.append("│")
    if has_main:
        lines.append("├── 🚀 Entry point detected")
    
    lines.append("│\n├── 📁 File Structure")
    
    for f in sorted_files:
        parts = f.split('/')
        depth = len(parts) - 1
        indent = "│   " * depth
        name = parts[-1]
        lines.append(f"{indent}├── 📄 {name} ({len(files_dict[f].splitlines())} lines)")
        
    return "\n".join(lines)

def scan_dependencies(files_dict):
    """Scans for dependencies in requirements.txt, package.json, or imports."""
    deps = set()
    
   
    if 'requirements.txt' in files_dict:
        for line in files_dict['requirements.txt'].splitlines():
            if line.strip() and not line.startswith('#'):
                pkg = line.strip().split('==')[0].split('>=')[0].split('<')[0]
                deps.add(f"🐍 {pkg}")
    
    if 'package.json' in files_dict:
        try:
            data = json.loads(files_dict['package.json'])
            for pkg in data.get('dependencies', {}).keys():
                deps.add(f"📦 {pkg}")
            for pkg in data.get('devDependencies', {}).keys():
                deps.add(f"🛠️ {pkg} (dev)")
        except: pass

    
    py_files = [f for f in files_dict if f.endswith('.py')][:5] 
    for f in py_files:
        matches = re.findall(r'^(?:import|from)\s+([a-zA-Z0-9_]+)', files_dict[f], re.MULTILINE)
        for m in matches:
            if m not in ['os', 'sys', 're', 'json', 'time', 'math']: 
                deps.add(f"🐍 {m}")

    return sorted(list(deps))

def extract_code_structure(files_dict):
    """Extracts classes and functions for a summary view."""
    structure = {}
   
    target_files = [f for f in files_dict if f.endswith(('.py', '.js', '.ts'))] 
    
    for filename in target_files[:200]: # Limit to 200 files
        content = files_dict[filename]
        

        if not content: continue
        
        classes = re.findall(r'class\s+([A-Za-z0-9_]+)', content)
        funcs = re.findall(r'def\s+([A-Za-z0-9_]+)', content)
        
        if classes or funcs:
            structure[filename] = {
                "classes": classes,
                "functions": funcs
            }
            
      
        del content
        
    return structure

def scan_security_issues(files_dict):
    """Scans for potential hardcoded secrets."""
    issues = []

    patterns = {
        "AWS Access Key": r"AKIA[0-9A-Z]{16}",
        "Generic Secret": r"(?i)(api_key|apikey|secret|password|token)\s*=\s*['\"][^'\"]+['\"]",
        "Private Key": r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"
    }
    
    for filename, content in files_dict.items():
     
        if len(content) > 100000: continue
        
        for issue_type, pattern in patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                
                lines = content.splitlines()
                line_nums = []
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        line_nums.append(i)
                
                issues.append({
                    "file": filename,
                    "type": issue_type,
                    "count": len(matches),
                    "lines": line_nums[:5] 
                })
    return issues

def scan_tech_debt(files_dict):
    """Scans for TODO, FIXME, HACK comments."""
    debt_items = []
    patterns = {
        "TODO": r"(?:#|//)\s*TODO:?\s*(.*)",
        "FIXME": r"(?:#|//)\s*FIXME:?\s*(.*)",
        "HACK": r"(?:#|//)\s*HACK:?\s*(.*)",
        "BUG": r"(?:#|//)\s*BUG:?\s*(.*)"
    }
    
    for name, content in files_dict.items():
     
        if not name.endswith(('.py', '.js', '.ts', '.java', '.go', '.rs', '.c', '.cpp')): continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            for tag, pat in patterns.items():
                match = re.search(pat, line, re.IGNORECASE)
                if match:
                    msg = match.group(1).strip() if match.groups() else ""
                    debt_items.append({
                        "file": name,
                        "line": i,
                        "type": tag,
                        "message": msg[:50]
                    })
    return debt_items

def detect_infrastructure(files_dict):
    """Detects framework and infra files."""
    detections = []
    checks = {
        "Docker": ["Dockerfile", "docker-compose.yml", ".dockerignore"],
        "Kubernetes": ["k8s/", "deployment.yaml", "helm/", "Chart.yaml"],
        "CI/CD": [".github/workflows/", ".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml"],
        "Tests": ["test_", "_test.py", ".spec.js", ".test.js", "tests/"],
        "Documentation": ["docs/", "mkdocs.yml", "sphinx/", "readthedocs.yaml"],
        "Config": [".env.example", "config.yaml", "settings.py"]
    }
    
    for tech, keys in checks.items():
        for key in keys:
            if any(key in f for f in files_dict):
                detections.append(tech)
                break
    return detections

def count_entities(files_dict):
    """Counts total classes, functions, and imports."""
    total = {"classes": 0, "functions": 0, "imports": 0}
    for name, content in files_dict.items():
        if not name.endswith(('.py', '.js', '.ts')): continue
        total['classes'] += len(re.findall(r'class\s+([A-Za-z0-9_]+)', content))
        total['functions'] += len(re.findall(r'def\s+([A-Za-z0-9_]+)', content))
        total['imports'] += len(re.findall(r'^(?:import|from)\s+', content, re.MULTILINE))
    return total

def extract_python_function_code(content, func_name):
    """
    Attempts to extract a specific function's code from Python content.
    Uses indentation logic to capture the full block.
    """
    lines = content.splitlines()
    code_lines = []
    recording = False
    base_indent = None
    
    for line in lines:
      
        if re.match(rf"^\s*def\s+{re.escape(func_name)}\s*\(", line):
            recording = True
         
            base_indent = len(line) - len(line.lstrip())
            code_lines.append(line)
            continue
            
        if recording:
          
            if not line.strip():
                code_lines.append(line)
                continue
                
            current_indent = len(line) - len(line.lstrip())
            
   
            if current_indent <= base_indent:
                break
            
            code_lines.append(line)
            
    return "\n".join(code_lines)

def get_zhipu_client():
    if not AI_AVAILABLE:
        return None
    
   
    api_key = os.environ.get("ZHIPUAI_API_KEY")
    
    if not api_key:
        return None
        
    return ZaiClient(api_key=api_key)

def ai_analyze_architecture(client, files_dict):
    """Generates a brief summary of the architecture using Rikai (GLM)."""
    if not client:
        return "⚠️ AI Analysis Failed: API Key not found."
    
    try:
     
        tree = build_full_tree(files_dict)
     
        if len(tree) > 3000:
            tree = tree[:3000] + "\n... (truncated)"
            
 
        readme_content = ""
        for fname in files_dict:
            if 'readme' in fname.lower():
                readme_content = files_dict[fname][:1000] 
                break
        
   
        prompt = f"""
        You are Rikai, an AI code architect. Analyze the following repository structure and README snippet.
        
        File Tree:
        {tree}
        
        README Snippet:
        {readme_content}
        
        Task:
        1. Identify the architectural pattern (e.g., MVC, Microservices, Library, CLI Tool).
        2. Summarize the purpose of this project in 2 sentences.
        3. Identify the likely entry point file.
        """
        

        response = client.chat.completions.create(
            model="GLM-4.7-Flash", 
            messages=[
                {"role": "system", "content": "You are Rikai, a senior software architect providing concise code reviews."},
                {"role": "user", "content": prompt}
            ],
        )
        return response.choices[0].message.content
        
    except Exception as e:
        return "We’re sorry. Something went wrong during the AI analysis. This may be due to a temporary server issue or high traffic or the repository might be too large. Please try again later."

def ai_explain_code(client, code_snippet, func_name):
    """Explains a specific function using Rikai (GLM)."""
    if not client:
        return "⚠️ AI Explanation Failed: API Key not found."
    
    try:
        prompt = f"""
        You are Rikai, an AI coding assistant. Explain the following Python function named '{func_name}'.
        Focus on:
        1. Inputs and Outputs.
        2. Core logic side effects.
        3. Potential edge cases or bugs.
        
        Code:
        ```
        {code_snippet}
        ```
        """
        
        response = client.chat.completions.create(
            model="GLM-4.7-Flash",
            messages=[
                {"role": "system", "content": "You are a coding assistant. Be concise and accurate."},
                {"role": "user", "content": prompt}
            ],
        )
        return response.choices[0].message.content
        
    except Exception as e:
        return "Unfortunately, an error occurred while explaining the code. The AI model might be temporarily unavailable or your API plan might have limitations."

def ai_project_synopsis(client, files_dict):
    """Generates a comprehensive project synopsis."""
    if not client: return "Error: No Client."
    
    tree = build_full_tree(files_dict)
    readme = ""
    for f in files_dict:
        if 'readme' in f.lower():
            readme = files_dict[f][:2000]
            break
    
    prompt = f"""
    You are Rikai, an expert Technical Product Manager. Based on the file tree and README, generate a Project Synopsis.
    
    File Tree:
    {tree[:2000]}
    
    README:
    {readme}
    
    Generate the following sections:
    1. **Executive Summary**: A 2-sentence high-level pitch.
    2. **Target Audience**: Who is this software for?
    3. **Problem Statement**: What problem does this code solve?
    4. **Key Features**: Bullet points of the top 3-5 features inferred from the files.
    """
    
    try:
        response = client.chat.completions.create(
            model="GLM-4.7-Flash",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating synopsis: {str(e)}"

def ai_review_file(client, filename, code_content):
    """Performs a code review on a specific file."""
    if not client: return "Error: No Client."
    
    # Truncate very long files to avoid token limits
    if len(code_content) > 4000:
        code_content = code_content[:4000] + "\n... (truncated for review)"
        
    prompt = f"""
    You are Rikai, a strict but helpful Code Reviewer. Review the following file '{filename}'.
    
    Code:
    ```
    {code_content}
    ```
    
    Provide a review with these sections:
    1. **Overview**: What does this file do?
    2. **Strengths**: What is done well?
    3. **Improvements**: Specific refactoring suggestions or performance tips.
    4. **Security Check**: Any obvious security concerns?
    5. **Style**: Comments on code style and readability.
    """
    
    try:
        response = client.chat.completions.create(
            model="GLM-4.7-Flash",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error reviewing file: {str(e)}"

def ai_onboarding_guide(client, files_dict, infra):
    """Creates a 'Getting Started' guide."""
    if not client: return "Error: No Client."
    
    tree = build_full_tree(files_dict)
    
    prompt = f"""
    You are Rikai, a DevOps Engineer. Create a "Getting Started / Onboarding" guide for a new developer.
    
    Project Structure:
    {tree[:2000]}
    
    Detected Infrastructure: {', '.join(infra)}
    
    Create a step-by-step guide covering:
    1. Prerequisites (Languages, DBs).
    2. Installation steps (clone, install deps).
    3. Configuration (env vars, config files).
    4. Running the project locally.
    5. Running tests (if detected).
    """
    
    try:
        response = client.chat.completions.create(
            model="GLM-4.7-Flash",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating guide: {str(e)}"

def ai_complexity_analysis(client, files_dict):
    """Analyzes code complexity and maintainability."""
    if not client: return "Error: No Client."
    
    
    sizes = []
    for f, c in files_dict.items():
        if c: 
            sizes.append(f"{f}: {len(c.splitlines())} lines")
    
    size_summary = "\n".join(sizes[:50]) # Top 50 files
    
    prompt = f"""
    You are Rikai, a Software Architect. Analyze the complexity of this project based on its file sizes and structure.
    
    File Sizes:
    {size_summary}
    
    Total Files: {len(files_dict)}
    
    Provide:
    1. **Complexity Rating**: Low / Medium / High / Critical.
    2. **Technical Debt Estimate**: Guess the level of technical debt.
    3. **Refactoring Advice**: General advice to simplify the codebase.
    """
    
    try:
        response = client.chat.completions.create(
            model="GLM-4.7-Flash",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error analyzing complexity: {str(e)}"

def ai_dependency_suggestions(client, files_dict):
    """Analyzes dependencies and suggests updates or alternatives."""
    if not client: return "Error: No Client."
    
    deps = scan_dependencies(files_dict)
    
    prompt = f"""
    You are Rikai, a Dependency Manager. Look at this list of project dependencies.
    
    Dependencies:
    {', '.join(deps)}
    
    Suggest:
    1. **Potential Outdated Packages**: Common packages that are often outdated.
    2. **Security Risks**: Known vulnerable patterns (generic).
    3. **Modern Alternatives**: Are there faster/modern libraries that could replace some of these?
    """
    
    try:
        response = client.chat.completions.create(
            model="GLM-4.7-Flash",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error analyzing dependencies: {str(e)}"

def ai_refactoring_ideas(client, files_dict):
    """Suggests refactoring ideas."""
    if not client: return "Error: No Client."
    
    tree = build_full_tree(files_dict)
    
    prompt = f"""
    You are Rikai, a Software Architect. Suggest refactoring ideas based on the file structure.
    
    Structure:
    {tree[:2000]}
    
    Suggest:
    1. **Code Organization**: Improving folder structure.
    2. **Design Patterns**: Patterns that might fit (Factory, Singleton, Strategy).
    3. **Modernization**: Updates to newer frameworks or language features.
    """
    
    try:
        response = client.chat.completions.create(
            model="GLM-4.7-Flash",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating refactoring ideas: {str(e)}"