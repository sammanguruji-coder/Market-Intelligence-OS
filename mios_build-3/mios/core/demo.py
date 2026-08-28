"""
Offline fixture corpus.

Demo mode exists for three reasons: you can open the app before your API
keys are wired, the UI can be developed without spending search quota,
and the pipeline has a deterministic corpus to test against.

The documents below are synthetic. They are written in the shape of real
market-research prose — including the definitional conflicts and global
vs local scope contamination that the reconciliation engine is built to
catch — but they are not reproductions of any publisher's text and the
figures should never be quoted as sourced fact.
"""

from __future__ import annotations

from typing import Dict, List

from . import search
from .domains import DOMAIN_IDS

_DOC = Dict[str, str]


def _doc(title: str, url: str, content: str) -> _DOC:
    return {"title": title, "url": url, "content": content, "raw_content": content}


# Deliberate features of this corpus:
#   * 2025 appears at USD 8.9B, 10.5B and 12.1B from different publishers
#     -> the reconciler must flag a definitional conflict, not average.
#   * A global USD 197B figure sits alongside India figures
#     -> contamination ratio must rise.
#   * Stated CAGRs (12.3 / 15.2 / 16.4) disagree with the implied CAGR
#     -> the rate-consistency check must fire.

CORPUS: Dict[int, List[_DOC]] = {
    1: [
        _doc(
            "India EdTech market size and forecast to 2030",
            "https://www.marketsandmarkets.example/india-edtech-market",
            "The India edtech market was valued at approximately USD 10.5 billion in "
            "2024 and is estimated to reach USD 12.1 billion in 2025. The market is "
            "projected to reach USD 29 billion by 2030 on continued digital adoption. "
            "Growth is concentrated in test preparation and professional upskilling "
            "rather than in core school delivery. The report defines the market to "
            "include hardware, content and services sold to institutions and consumers.",
        ),
        _doc(
            "India online education market outlook",
            "https://www.imarcgroup.example/india-online-education-market",
            "India's online education market reached USD 7.5 billion in 2024 on a "
            "narrower definition that excludes classroom hardware and device sales. "
            "The market is expected to grow at a CAGR of 15.2% between 2025 and 2035. "
            "Definitional differences across published estimates are substantial and "
            "readers should reconcile scope before comparing figures.",
        ),
        _doc(
            "India edtech and smart classrooms market statistics",
            "https://www.researchhouse.example/india-edtech-smart-classrooms",
            "Market size in 2025 stands at approximately USD 8.9 billion with a "
            "forecast of USD 19.0 billion by 2030, implying a 16.4% CAGR over the "
            "period. Hardware represented 40.5% of market participation in 2025, "
            "reflecting continued institutional investment in physical digital "
            "infrastructure across India.",
        ),
        _doc(
            "Global EdTech and smart classrooms market growth outlook",
            "https://www.globalresearch.example/edtech-smart-classrooms",
            "The global EdTech and smart classrooms market is expected to grow from "
            "approximately USD 197.3 billion in 2025 to USD 353.1 billion by 2030, at "
            "a CAGR of around 12.3% during the forecast period. Asia Pacific accounts "
            "for the largest incremental contribution to worldwide growth.",
        ),
    ],
    2: [
        _doc(
            "Segment structure of India's edtech market",
            "https://www.skydo.example/edtech-market-india",
            "Test preparation accounted for 38% of India edtech revenue in 2025, the "
            "largest single segment. K-12 supplementary learning held a share of 43% "
            "in 2025 by user volume though a smaller share of revenue. Professional "
            "upskilling contributed 21% of revenue and is the fastest growing segment "
            "measured by paid enrolments.",
        ),
        _doc(
            "B2B versus B2C split in Indian education technology",
            "https://www.indiamarketentry.example/edtech-b2b-opportunity",
            "Direct-to-consumer models represented 72% of funded companies but a "
            "declining share of new revenue. Institutional and B2B sales to schools "
            "and colleges accounted for 28% of the market in 2025 and are growing "
            "faster than consumer subscriptions as customer acquisition costs rise.",
        ),
    ],
    3: [
        _doc(
            "Demand drivers in Indian digital learning",
            "https://www.tradebody.example/india-edtech-demand",
            "Household spending on education is the second largest discretionary "
            "category for Indian families after groceries. Internet penetration "
            "reached 52% of the population in 2025 and affordable data packages have "
            "extended reach into tier-2 and tier-3 cities. Demand for test preparation "
            "is structurally tied to examination cohorts that grow with school "
            "enrolment rather than with economic cycles.",
        ),
        _doc(
            "Willingness to pay for online learning in India",
            "https://www.consumerpanel.example/india-learning-spend",
            "Average annual spend per paying learner rose 14% in 2025 to around USD "
            "118. Conversion from free to paid tiers remains under 4% for consumer "
            "platforms, indicating that demand is broad but shallow at current price "
            "points. Willingness to pay is materially higher for outcome-linked "
            "products such as certification and placement support.",
        ),
    ],
    4: [
        _doc(
            "Business model shifts in education technology",
            "https://www.newmarketpitch.example/edtech-business-model",
            "The industry is shifting from content subscription toward creator "
            "infrastructure, where platforms charge educators for tooling, payments "
            "and storefronts rather than charging learners directly. Take rates on "
            "creator platforms run between 8% and 15%, materially above the "
            "contribution margin of discount-led consumer subscriptions.",
        ),
        _doc(
            "Consolidation and correction in Indian edtech",
            "https://www.businesspress.example/edtech-correction",
            "Following the funding correction, marketing-led growth has given way to "
            "unit economics discipline. Several large players reduced customer "
            "acquisition spending by more than 40% in 2025 while raising prices, "
            "trading growth for contribution margin.",
        ),
    ],
    5: [
        _doc(
            "Competitive landscape of India edtech",
            "https://www.globaldata.example/india-edtech-competition",
            "The India edtech market exhibits a moderately fragmented competitive "
            "landscape, with established platforms competing alongside emerging "
            "startups. The largest player holds an estimated share of 18% of paid "
            "consumer enrolments. No participant holds a dominant position in "
            "institutional sales, where regional providers retain long-standing "
            "school relationships.",
        ),
        _doc(
            "Barriers to entry in Indian digital education",
            "https://www.advisory.example/edtech-entry-barriers",
            "Brand trust and distribution into schools are the principal barriers to "
            "entry rather than technology. Switching costs for institutions are high "
            "once a learning platform is embedded in timetabling and assessment, "
            "creating durable lock-in for incumbent vendors.",
        ),
    ],
    6: [
        _doc(
            "Leading education technology companies in India",
            "https://www.leadsquared.example/edtech-companies-in-india",
            "The ten largest platforms by revenue collectively serve over 40 million "
            "registered learners. Combined revenue of the top five reached USD 2.4 "
            "billion in 2025. Investment has shifted toward profitability, with three "
            "of the five largest reporting positive contribution margin for the first "
            "time.",
        ),
        _doc(
            "Funding activity in Indian education technology",
            "https://www.tracxn.example/india-edtech-funding",
            "Disclosed funding into Indian edtech totalled USD 1.1 billion in 2025, "
            "down from the 2021 peak. Late-stage capital is concentrated in "
            "profitable upskilling and certification businesses rather than in "
            "consumer K-12 platforms.",
        ),
    ],
    7: [
        _doc(
            "Value chain economics of education technology",
            "https://www.advisory.example/edtech-value-chain",
            "Content production, learner acquisition, delivery infrastructure and "
            "assessment form the four principal cost pools. Gross margin on digital "
            "content delivery runs between 65% and 78% once content is amortised, but "
            "customer acquisition cost consumes the majority of first-year revenue in "
            "consumer models. The control point sits at assessment and credentialing, "
            "where switching costs and pricing power are highest.",
        ),
        _doc(
            "Unit economics of Indian learning platforms",
            "https://www.equityresearch.example/edtech-unit-economics",
            "Blended customer acquisition cost averaged USD 46 against first-year "
            "revenue of USD 118, giving a payback period of roughly nine months for "
            "the better operators. Lifetime value to CAC ratios cluster near 2.1x, "
            "below the 3x threshold generally required for capital-efficient scaling.",
        ),
    ],
    8: [
        _doc(
            "Regulatory landscape for edtech companies in India",
            "https://www.schoolnet.example/edtech-regulation-india",
            "The National Education Policy explicitly promotes digital education and "
            "the government has introduced incentive schemes supporting digital "
            "infrastructure in schools. Self-regulation guidelines mandate refund "
            "windows and restrict aggressive sales practices to minors. Data "
            "localisation requirements raise compliance cost for platforms handling "
            "learner records.",
        ),
        _doc(
            "Compliance obligations for education platforms",
            "https://www.legalpractice.example/edtech-compliance",
            "Platforms must register under consumer protection rules and comply with "
            "advertising standards specific to educational outcomes claims. Scrutiny "
            "of outcome guarantees increased through 2025, with penalties introduced "
            "for unsubstantiated placement claims.",
        ),
    ],
    9: [
        _doc(
            "Technology adoption in Indian education",
            "https://www.trade.example/india-education-technology",
            "Adaptive assessment and automated content generation have reduced content "
            "production cost per hour by an estimated 35% since 2023. Cloud delivery "
            "has removed most fixed infrastructure cost for new entrants, shifting the "
            "constraint from capital to distribution.",
        ),
        _doc(
            "Vernacular delivery and regional language platforms",
            "https://www.techanalysis.example/vernacular-edtech",
            "India has multiple official languages and hundreds of regional dialects, "
            "creating significant opportunity for edtech platforms offering localised "
            "content. Vernacular content expansion into tier-2 and tier-3 markets is "
            "the largest untapped demand pool identified by platform operators.",
        ),
    ],
    10: [
        _doc(
            "Customer segments in Indian education technology",
            "https://www.holoniq.example/india-edtech-customers",
            "India is home to approximately 250 million K-12 learners across 1.5 "
            "million schools. Parents are the payer for school-age products while the "
            "learner is the user, creating a split decision unit. In professional "
            "upskilling the learner is the payer and purchase criteria centre on "
            "placement outcomes rather than content quality.",
        ),
        _doc(
            "Institutional buying behaviour in Indian education",
            "https://www.consultancy.example/institutional-edtech-buying",
            "Institutional purchase cycles run nine to fourteen months and are "
            "budget-anchored to the academic year. Price sensitivity is high and "
            "discounting is routine, with published list prices realised at an "
            "average of 62%.",
        ),
    ],
    11: [
        _doc(
            "Returns and profitability in edtech",
            "https://www.equityresearch.example/edtech-returns",
            "Operating margin for the profitable cohort of Indian platforms reached "
            "9% in 2025, against sustained losses across the consumer K-12 cohort. "
            "Return on invested capital remains below the cost of capital for all but "
            "the certification and enterprise training businesses.",
        ),
        _doc(
            "Investment attractiveness of India's education sector",
            "https://www.investindia.example/edtech-opportunities",
            "Despite the funding correction, India's edtech industry retains a large "
            "addressable base and strong policy support. Monetisation of institutional "
            "channels is improving as procurement budgets shift from hardware toward "
            "recurring software and assessment services.",
        ),
    ],
    12: [
        _doc(
            "Growth pools in Indian digital learning",
            "https://www.researchnester.example/education-technology-market",
            "Government-backed digital education initiatives and capital spending on "
            "the modernisation of education infrastructure are expected to boost "
            "demand for online learning technologies. The strongest identified pools "
            "are vernacular content expansion, assessment and credentialing services, "
            "and enterprise upskilling.",
        ),
        _doc(
            "Whitespace in Indian education technology",
            "https://www.strategyhouse.example/edtech-whitespace",
            "Assessment and credentialing services remain underserved relative to "
            "content, with fewer than a dozen credible providers against a market of "
            "1.5 million schools. Demand for personalised learning solutions is "
            "growing but monetisation is unproven outside test preparation.",
        ),
    ],
    13: [
        _doc(
            "Risks and challenges in India's edtech industry",
            "https://www.policycentre.example/edtech-risks-india",
            "Many Indian edtech companies operate on aggressive marketing-led growth "
            "strategies, leading to high customer acquisition costs and delayed "
            "profitability. The 2022 to 2024 funding winter produced layoffs, "
            "write-downs and at least one large-scale insolvency. Churn on consumer "
            "subscriptions exceeds 60% annually for platforms without outcome "
            "guarantees.",
        ),
        _doc(
            "Governance and disclosure concerns in education technology",
            "https://www.esgresearch.example/edtech-esg-outlook",
            "Regulatory scrutiny of refund practices and outcome claims increased "
            "through 2025. Concentration of revenue in test preparation exposes "
            "operators to examination policy changes. Margin pressure from discounting "
            "persists across the consumer segment.",
        ),
    ],
}


def install(industry: str, geography: str, objective: str) -> None:
    """Prime the search cache so a full run works with no network."""
    entries: Dict[str, List[_DOC]] = {}
    for domain_id in DOMAIN_IDS:
        docs = CORPUS.get(domain_id, [])
        for query in search.build_queries(industry, geography, objective, domain_id):
            entries[query] = docs
    search.prime_cache(entries)


def available_for(industry: str) -> bool:
    return "edtech" in (industry or "").lower() or "education" in (industry or "").lower()


__all__ = ["CORPUS", "available_for", "install"]
