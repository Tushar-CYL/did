"""Tools / skills extraction — the core intel.

Scans a job description (+ title) for enterprise tools and maps each to a
"practice" bucket (Data & AI, SAP/ERP, Cloud, Cyber, Salesforce/CRM, Finance
tools, Supply Chain tools, Automation). This is what the account teams care
about: WHICH tools a client is hiring for inside each department.
"""
from __future__ import annotations

import re

# practice -> { canonical tool : [aliases...] }  (aliases matched case-insensitively,
# short tokens on word boundaries to avoid false positives)
PRACTICE_TOOLS: dict[str, dict[str, list[str]]] = {
    "Data & AI": {
        "SQL": ["sql"], "Python": ["python"], "Power BI": ["power bi", "powerbi"],
        "Tableau": ["tableau"], "Qlik": ["qlik"], "Looker": ["looker"],
        "Databricks": ["databricks"], "Snowflake": ["snowflake"], "Spark": ["spark", "pyspark"],
        "Kafka": ["kafka"], "Airflow": ["airflow"], "dbt": ["dbt"], "SAS": ["\\bsas\\b"],
        "Alteryx": ["alteryx"], "Hadoop": ["hadoop"], "GenAI": ["genai", "gen ai", "generative ai"],
        "LLM": ["\\bllm\\b", "large language model"], "Machine Learning": ["machine learning"],
        "Azure ML": ["azure ml", "azure machine learning"], "TensorFlow": ["tensorflow"],
        "PyTorch": ["pytorch"], "Data Governance": ["data governance"], "MDM": ["\\bmdm\\b"],
    },
    "SAP / ERP": {
        "SAP": ["\\bsap\\b"], "S/4HANA": ["s/4hana", "s4hana", "s/4 hana"], "SAP ABAP": ["abap"],
        "SAP FICO": ["fico"], "SAP MM": ["\\bsap mm\\b"], "SAP SD": ["\\bsap sd\\b"],
        "SAP BW": ["\\bsap bw\\b", "\\bbw/4hana\\b"], "SAP Ariba": ["ariba"],
        "SuccessFactors": ["successfactors", "success factors"], "SAP IBP": ["\\bibp\\b"],
        "Oracle ERP": ["oracle erp", "oracle fusion", "oracle ebs", "e-business suite"],
        "Dynamics 365": ["dynamics 365", "d365", "ms dynamics"], "NetSuite": ["netsuite"],
        "Coupa": ["coupa"], "Anaplan": ["anaplan"], "Workday": ["workday"], "PeopleSoft": ["peoplesoft"],
    },
    "Cloud & Infra": {
        "Azure": ["\\bazure\\b"], "AWS": ["\\baws\\b", "amazon web services"],
        "GCP": ["\\bgcp\\b", "google cloud"], "Kubernetes": ["kubernetes", "\\bk8s\\b"],
        "Docker": ["docker"], "Terraform": ["terraform"], "DevOps": ["devops"],
        "CI/CD": ["ci/cd", "ci cd"], "OpenShift": ["openshift"], "VMware": ["vmware"],
    },
    "Cyber": {
        "Cybersecurity": ["cybersecurity", "cyber security"], "IAM": ["\\biam\\b", "identity and access"],
        "SailPoint": ["sailpoint"], "Okta": ["\\bokta\\b"], "CyberArk": ["cyberark"],
        "SIEM": ["\\bsiem\\b"], "Splunk": ["splunk"], "SOC": ["\\bsoc\\b"], "CISSP": ["cissp"],
        "Penetration Testing": ["penetration testing", "pen testing"], "CrowdStrike": ["crowdstrike"],
        "Palo Alto": ["palo alto"], "Zscaler": ["zscaler"],
    },
    "Salesforce / CRM": {
        "Salesforce": ["salesforce"], "Service Cloud": ["service cloud"], "Sales Cloud": ["sales cloud"],
        "Marketing Cloud": ["marketing cloud"], "ServiceNow": ["servicenow", "service now"],
        "Dynamics CRM": ["dynamics crm"], "HubSpot": ["hubspot"], "Adobe Experience": ["adobe experience", "\\baem\\b"],
    },
    "Finance tools": {
        "HighRadius": ["highradius", "high radius"], "BlackLine": ["blackline", "black line"],
        "OneStream": ["onestream"], "Oracle EPM": ["oracle epm", "\\bepm\\b"], "Hyperion": ["hyperion"],
        "Tagetik": ["tagetik"], "Kyriba": ["kyriba"], "Trintech": ["trintech"],
    },
    "Supply Chain tools": {
        "Blue Yonder": ["blue yonder", "blueyonder", "\\bjda\\b"], "Kinaxis": ["kinaxis"],
        "o9": ["\\bo9\\b"], "Manhattan": ["manhattan associates"], "OMP": ["\\bomp\\b"],
        "e2open": ["e2open"],
    },
    "Automation": {
        "UiPath": ["uipath", "ui path"], "Automation Anywhere": ["automation anywhere"],
        "Blue Prism": ["blue prism"], "Power Automate": ["power automate"],
        "Celonis": ["celonis", "process mining"], "Pega": ["\\bpega\\b"],
    },
}

# pre-compile: list of (canonical, practice, compiled_regex)
_COMPILED: list[tuple[str, str, re.Pattern]] = []
for _practice, _tools in PRACTICE_TOOLS.items():
    for _canon, _aliases in _tools.items():
        parts = []
        for a in _aliases:
            parts.append(a if a.startswith("\\b") or "\\b" in a else re.escape(a))
        _COMPILED.append((_canon, _practice, re.compile("|".join(parts), re.IGNORECASE)))

PRACTICES = list(PRACTICE_TOOLS.keys())


def extract(text: str) -> tuple[list[str], list[str]]:
    """Return (tools, practices) found in the text. Order-preserving, de-duplicated."""
    if not text:
        return [], []
    tools: list[str] = []
    practices: list[str] = []
    seen_t, seen_p = set(), set()
    for canon, practice, rx in _COMPILED:
        if rx.search(text):
            if canon not in seen_t:
                seen_t.add(canon); tools.append(canon)
            if practice not in seen_p:
                seen_p.add(practice); practices.append(practice)
    return tools, practices
