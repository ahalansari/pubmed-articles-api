"""
PubMed E-utilities API Client
Handles all interactions with NCBI PubMed and PubMed Central APIs
"""

import requests
import xml.etree.ElementTree as ET
from typing import Optional
import time
import re


class PubMedClient:
    """Client for interacting with PubMed E-utilities and PMC APIs"""
    
    EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    PMC_OA_BASE = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
    PMC_ID_CONVERTER = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    
    def __init__(self, api_key: Optional[str] = None, email: Optional[str] = None, tool: str = "pubmed-articles-api"):
        self.api_key = api_key
        self.email = email
        self.tool = tool
        self.last_request_time = 0
        self.min_request_interval = 0.34 if api_key else 1.0
    
    def _rate_limit(self):
        """Enforce rate limiting for NCBI API"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _get_base_params(self) -> dict:
        """Get base parameters for all E-utilities requests"""
        params = {"tool": self.tool}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email
        return params
    
    def search(self, query: str, max_results: int = 10, sort: str = "relevance") -> dict:
        """
        Search PubMed for articles matching the query
        
        Args:
            query: Search query (supports PubMed syntax)
            max_results: Maximum number of results to return (1-100)
            sort: Sort order - "relevance" or "date"
        
        Returns:
            dict with pmids list and total count
        """
        self._rate_limit()
        
        params = self._get_base_params()
        params.update({
            "db": "pubmed",
            "term": query,
            "retmax": min(max_results, 100),
            "retmode": "json",
            "sort": sort
        })
        
        response = requests.get(f"{self.EUTILS_BASE}/esearch.fcgi", params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        esearch_result = data.get("esearchresult", {})
        
        return {
            "pmids": esearch_result.get("idlist", []),
            "total_count": int(esearch_result.get("count", 0)),
            "query_translation": esearch_result.get("querytranslation", query)
        }
    
    def get_article_summaries(self, pmids: list) -> list:
        """
        Get summary information for a list of PMIDs
        
        Args:
            pmids: List of PubMed IDs
        
        Returns:
            List of article summary dictionaries
        """
        if not pmids:
            return []
        
        self._rate_limit()
        
        params = self._get_base_params()
        params.update({
            "db": "pubmed",
            "id": ",".join(str(p) for p in pmids),
            "retmode": "json"
        })
        
        response = requests.get(f"{self.EUTILS_BASE}/esummary.fcgi", params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        result = data.get("result", {})
        
        articles = []
        for pmid in pmids:
            pmid_str = str(pmid)
            if pmid_str in result:
                article = result[pmid_str]
                articles.append({
                    "pmid": pmid_str,
                    "title": article.get("title", ""),
                    "authors": self._format_authors(article.get("authors", [])),
                    "journal": article.get("fulljournalname", article.get("source", "")),
                    "pub_date": article.get("pubdate", ""),
                    "doi": self._extract_doi(article.get("elocationid", "")),
                    "pmcid": article.get("pmcid", ""),
                    "pub_types": article.get("pubtype", [])
                })
        
        return articles
    
    def get_article_details(self, pmids: list) -> list:
        """
        Get full article details including abstract for a list of PMIDs
        
        Args:
            pmids: List of PubMed IDs
        
        Returns:
            List of article detail dictionaries with abstracts
        """
        if not pmids:
            return []
        
        self._rate_limit()
        
        params = self._get_base_params()
        params.update({
            "db": "pubmed",
            "id": ",".join(str(p) for p in pmids),
            "rettype": "abstract",
            "retmode": "xml"
        })
        
        response = requests.get(f"{self.EUTILS_BASE}/efetch.fcgi", params=params, timeout=60)
        response.raise_for_status()
        
        return self._parse_pubmed_xml(response.text)
    
    def get_pmc_full_text(self, pmcid: str) -> Optional[str]:
        """
        Get full text from PubMed Central for open access articles
        
        Args:
            pmcid: PubMed Central ID (e.g., "PMC1234567")
        
        Returns:
            Full text content or None if not available
        """
        pmcid_clean = pmcid.replace("PMC", "")
        
        self._rate_limit()
        
        params = {"id": f"PMC{pmcid_clean}"}
        response = requests.get(self.PMC_OA_BASE, params=params, timeout=30)
        
        if response.status_code != 200:
            return None
        
        try:
            root = ET.fromstring(response.text)
            error = root.find(".//error")
            if error is not None:
                return None
            
            link = root.find(".//link[@format='xml']")
            if link is None:
                link = root.find(".//link[@format='tgz']")
            
            if link is not None:
                href = link.get("href")
                if href and href.endswith(".xml"):
                    return self._fetch_pmc_xml_content(href)
            
            return None
            
        except ET.ParseError:
            return None
    
    def _fetch_pmc_xml_content(self, url: str) -> Optional[str]:
        """Fetch and parse PMC XML to extract article text"""
        try:
            self._rate_limit()
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            
            text_parts = []
            
            abstract = root.find(".//abstract")
            if abstract is not None:
                text_parts.append("ABSTRACT:\n" + self._extract_text(abstract))
            
            body = root.find(".//body")
            if body is not None:
                for sec in body.findall(".//sec"):
                    title = sec.find("title")
                    if title is not None and title.text:
                        text_parts.append(f"\n{title.text.upper()}:")
                    for p in sec.findall(".//p"):
                        text_parts.append(self._extract_text(p))
            
            return "\n\n".join(text_parts) if text_parts else None
            
        except Exception:
            return None
    
    def convert_pmid_to_pmcid(self, pmids: list) -> dict:
        """
        Convert PMIDs to PMCIDs where available
        
        Args:
            pmids: List of PubMed IDs
        
        Returns:
            Dictionary mapping PMID to PMCID (only for articles in PMC)
        """
        if not pmids:
            return {}
        
        self._rate_limit()
        
        params = {
            "ids": ",".join(str(p) for p in pmids),
            "format": "json",
            "tool": self.tool
        }
        if self.email:
            params["email"] = self.email
        
        response = requests.get(self.PMC_ID_CONVERTER, params=params, timeout=30)
        
        if response.status_code != 200:
            return {}
        
        try:
            data = response.json()
            mapping = {}
            for record in data.get("records", []):
                pmid = record.get("pmid")
                pmcid = record.get("pmcid")
                if pmid and pmcid:
                    mapping[str(pmid)] = pmcid
            return mapping
        except Exception:
            return {}
    
    def _parse_pubmed_xml(self, xml_content: str) -> list:
        """Parse PubMed XML response to extract article details"""
        articles = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for article in root.findall(".//PubmedArticle"):
                medline = article.find("MedlineCitation")
                if medline is None:
                    continue
                
                pmid_elem = medline.find("PMID")
                pmid = pmid_elem.text if pmid_elem is not None else ""
                
                article_elem = medline.find("Article")
                if article_elem is None:
                    continue
                
                title_elem = article_elem.find("ArticleTitle")
                title = self._extract_text(title_elem) if title_elem is not None else ""
                
                abstract_elem = article_elem.find("Abstract")
                abstract = ""
                if abstract_elem is not None:
                    abstract_texts = []
                    for abstract_text in abstract_elem.findall("AbstractText"):
                        label = abstract_text.get("Label", "")
                        text = self._extract_text(abstract_text)
                        if label:
                            abstract_texts.append(f"{label}: {text}")
                        else:
                            abstract_texts.append(text)
                    abstract = "\n\n".join(abstract_texts)
                
                journal_elem = article_elem.find("Journal")
                journal = ""
                pub_date = ""
                if journal_elem is not None:
                    journal_title = journal_elem.find("Title")
                    journal = journal_title.text if journal_title is not None else ""
                    
                    journal_issue = journal_elem.find("JournalIssue")
                    if journal_issue is not None:
                        pub_date_elem = journal_issue.find("PubDate")
                        if pub_date_elem is not None:
                            year = pub_date_elem.find("Year")
                            month = pub_date_elem.find("Month")
                            pub_date = f"{year.text if year is not None else ''}"
                            if month is not None and month.text:
                                pub_date = f"{month.text} {pub_date}"
                
                authors = []
                author_list = article_elem.find("AuthorList")
                if author_list is not None:
                    for author in author_list.findall("Author"):
                        lastname = author.find("LastName")
                        forename = author.find("ForeName")
                        if lastname is not None:
                            name = lastname.text
                            if forename is not None and forename.text:
                                name = f"{forename.text} {name}"
                            authors.append(name)
                
                keywords = []
                keyword_list = medline.find("KeywordList")
                if keyword_list is not None:
                    for kw in keyword_list.findall("Keyword"):
                        if kw.text:
                            keywords.append(kw.text)
                
                mesh_terms = []
                mesh_list = medline.find("MeshHeadingList")
                if mesh_list is not None:
                    for mesh in mesh_list.findall("MeshHeading"):
                        descriptor = mesh.find("DescriptorName")
                        if descriptor is not None and descriptor.text:
                            mesh_terms.append(descriptor.text)
                
                pub_types = []
                pub_type_list = article_elem.find("PublicationTypeList")
                if pub_type_list is not None:
                    for pt in pub_type_list.findall("PublicationType"):
                        if pt.text:
                            pub_types.append(pt.text)
                
                doi = ""
                pubmed_data = article.find("PubmedData")
                if pubmed_data is not None:
                    article_ids = pubmed_data.find("ArticleIdList")
                    if article_ids is not None:
                        for aid in article_ids.findall("ArticleId"):
                            if aid.get("IdType") == "doi":
                                doi = aid.text
                                break
                
                articles.append({
                    "pmid": pmid,
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "journal": journal,
                    "pub_date": pub_date,
                    "doi": doi,
                    "keywords": keywords,
                    "mesh_terms": mesh_terms,
                    "pub_types": pub_types
                })
        
        except ET.ParseError:
            pass
        
        return articles
    
    def _extract_text(self, element) -> str:
        """Extract all text from an XML element, including nested elements"""
        if element is None:
            return ""
        return "".join(element.itertext()).strip()
    
    def _format_authors(self, authors_list: list) -> list:
        """Format authors from esummary response"""
        formatted = []
        for author in authors_list:
            name = author.get("name", "")
            if name:
                formatted.append(name)
        return formatted
    
    def _extract_doi(self, elocationid: str) -> str:
        """Extract DOI from elocationid field"""
        if not elocationid:
            return ""
        match = re.search(r'10\.\d+/[^\s]+', elocationid)
        return match.group(0) if match else ""

