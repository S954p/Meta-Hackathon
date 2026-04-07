from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class KBArticle:
    kb_topic: str
    title: str
    body: str


KB: Dict[str, List[KBArticle]] = {
    "password_reset": [
        KBArticle(
            kb_topic="password_reset",
            title="Resetting your password (customer guide)",
            body=(
                "To reset your password:\n"
                "1) Go to the sign-in page.\n"
                "2) Click 'Forgot password'.\n"
                "3) Enter your account email.\n"
                "4) Check your inbox for the reset link.\n"
                "5) Open the link and set a new password.\n"
                "If you don't receive the email within 10 minutes, check spam or request again."
            ),
        ),
        KBArticle(
            kb_topic="password_reset",
            title="Account access and sign-in issues",
            body=(
                "If login still fails after a reset:\n"
                "1) Confirm you are using the correct account email.\n"
                "2) Clear browser cache or try an incognito window.\n"
                "3) Disable VPN/proxy temporarily and retry the reset link.\n"
            ),
        ),
    ],
    "billing_double_charge_missing_info": [
        KBArticle(
            kb_topic="billing_double_charge_missing_info",
            title="Double charge investigation (billing team)",
            body=(
                "If a customer reports a double charge:\n"
                "1) Collect the invoice number (or receipt ID) and the billing month.\n"
                "2) Verify the payment reference on the ledger.\n"
                "3) If two captures exist, identify whether one is a duplicate authorization.\n"
                "4) Apply a refund for the duplicate capture and confirm the refund timeline."
            ),
        ),
        KBArticle(
            kb_topic="billing_double_charge_missing_info",
            title="Subscription billing and duplicate captures",
            body=(
                "Common causes of apparent double charges:\n"
                "1) Pending authorization plus settled charge (explain timeline).\n"
                "2) Different billing cycles overlapping after plan change.\n"
                "Always match invoice IDs and billing month before issuing a refund."
            ),
        ),
    ],
    "technical_wifi_disconnect_troubleshooting": [
        KBArticle(
            kb_topic="technical_wifi_disconnect_troubleshooting",
            title="Wi-Fi disconnect after update (troubleshooting)",
            body=(
                "Troubleshooting steps for recurring Wi-Fi disconnects:\n"
                "1) Forget the network and reconnect.\n"
                "2) Power-cycle the router (unplug 30 seconds).\n"
                "3) Check that router firmware is up to date.\n"
                "4) Verify DNS settings (use automatic or reputable DNS).\n"
                "5) Try switching Wi-Fi band (2.4 GHz vs 5 GHz) if supported.\n"
            ),
        ),
        KBArticle(
            kb_topic="technical_wifi_disconnect_troubleshooting",
            title="When DNS misconfiguration causes disconnects",
            body=(
                "If disconnects happen frequently after an update:\n"
                "1) Ensure DNS is set to Automatic (or equivalent).\n"
                "2) Test by switching to a public DNS and retesting stability.\n"
            ),
        ),
    ],
}


def search_kb(query: str) -> List[KBArticle]:
    """
    Deterministic keyword scoring retrieval.
    Prevents cross-topic mismatches (e.g. Wi-Fi -> password reset).
    """
    q = (query or "").lower()
    topic_keywords: Dict[str, List[str]] = {
        "password_reset": [
            "password",
            "forgot password",
            "reset",
            "reset link",
            "login",
            "log in",
            "signin",
            "sign in",
            "account access",
        ],
        "billing_double_charge_missing_info": [
            "billing",
            "invoice",
            "double charge",
            "charged twice",
            "refund",
            "receipt",
            "subscription",
            "payment",
        ],
        "technical_wifi_disconnect_troubleshooting": [
            "wifi",
            "wi-fi",
            "wireless",
            "disconnect",
            "dropping",
            "router",
            "dns",
            "band",
            "firmware",
            "network unstable",
        ],
    }
    topic_scores: Dict[str, int] = {k: 0 for k in topic_keywords.keys()}
    for topic, keywords in topic_keywords.items():
        score = 0
        for kw in keywords:
            if kw in q:
                # Give a slightly higher weight to multi-word phrases.
                score += 2 if " " in kw else 1
        topic_scores[topic] = score

    best_topic = max(topic_scores, key=topic_scores.get)
    best_score = topic_scores[best_topic]
    matches: List[KBArticle] = []
    if best_score > 0:
        matches.extend(KB.get(best_topic, []))
    else:
        # Unclear query: return one article per topic as neutral context.
        for topic in (
            "password_reset",
            "billing_double_charge_missing_info",
            "technical_wifi_disconnect_troubleshooting",
        ):
            articles = KB.get(topic, [])
            if articles:
                matches.append(articles[0])

    # Deduplicate while preserving order (by title).
    seen_titles: set[str] = set()
    deduped: List[KBArticle] = []
    for a in matches:
        if a.title in seen_titles:
            continue
        seen_titles.add(a.title)
        deduped.append(a)
    return deduped

