"""Shared purpose-specific writing requirements and audience defaults."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PurposeGuide:
    label: str
    recipient: str
    intent: str
    subject: str
    salutation: str
    closing: str
    avoid: str


PURPOSE_GUIDES = (
    PurposeGuide(
        "Bitte um Zuweisung von Geldauflagen",
        "Gerichte und Staatsanwaltschaften",
        "Ask judicial decision-makers to allocate monetary penalties to LAIKA's work.",
        "A formal subject about allocating Geldauflagen to support bereavement care.",
        "Use a formal greeting, for example 'Sehr geehrte Damen und Herren,'. Adapt to a named recipient if supplied.",
        "Make a clear request for the allocation of Geldauflagen, followed by thanks and a formal closing.",
        "Do not address courts as private donors or imply they have already allocated funds.",
    ),
    PurposeGuide(
        "Spendenaufruf",
        "Private Spenderinnen und Spender sowie Unterstützende",
        "Invite private supporters to make a voluntary donation, explaining what their support enables.",
        "Create an inviting donation subject, for example 'Mit Ihrer Spende trauernden Kindern Halt geben'.",
        "Address supporters warmly, for example 'Liebe Unterstützerinnen und Unterstützer,'. Respect a supplied named recipient.",
        "Invite a voluntary donation and thank the reader for considering support; invent no bank details or donation links.",
        "Do not ask for allocations of fines, Geldauflagen or Bußgelder, or copy the judicial appeal's subject or greeting by default.",
    ),
    PurposeGuide(
        "Förderanfrage",
        "Stiftungen und Förderinstitutionen",
        "Ask a foundation or funding institution to consider supporting LAIKA, describing its work and funding need.",
        "Create a funding-enquiry subject, for example 'Förderanfrage zur tiergestützten Trauerbegleitung bei LAIKA'.",
        "Use a formal institutional greeting; adapt it to a supplied contact without inventing a name.",
        "Invite a conversation about potential funding or the institution's application process; invent no budget or project commitments.",
        "Do not request allocations of monetary penalties or address the institution as a court.",
    ),
    PurposeGuide(
        "Dankesschreiben",
        "Spenderinnen, Spender und Unterstützende von LAIKA",
        "Express appreciation for support already received or the recipient's commitment. Lead with gratitude, not financial need.",
        "Create a gratitude-led subject, for example 'Herzlichen Dank für Ihre Unterstützung'.",
        "Use an appreciative greeting, for example 'Liebe Unterstützerinnen und Unterstützer,'. Personalize only from supplied details.",
        "End with sincere appreciation and goodwill. Do not make a new donation, funding or fine-allocation request.",
        "Do not turn the thank-you into an appeal. Do not invent a gift, amount or completed activity. Mention past fine allocations only if the brief explicitly identifies that support.",
    ),
    PurposeGuide(
        "Allgemeines Vereinsschreiben",
        "Interessierte und Kontakte des Vereins",
        "Introduce or inform readers about LAIKA and the topic in the brief, without assuming fundraising is the goal.",
        "Create an informative subject specific to the brief, for example 'Ein Einblick in die Arbeit von LAIKA'.",
        "Choose a greeting suitable for the actual audience; do not inherit the judicial audience from historical examples.",
        "Close with an appropriate invitation to learn more or get in touch. Include a financial request only when the brief explicitly asks for it.",
        "Do not automatically request donations, funding or Geldauflagen, or reuse an old appeal's subject.",
    ),
)
PURPOSE_LABELS = tuple(guide.label for guide in PURPOSE_GUIDES)


def purpose_guide(purpose: str) -> PurposeGuide:
    normalized = purpose.strip().casefold()
    if normalized == "dankeschreiben":
        normalized = "dankesschreiben"
    for guide in PURPOSE_GUIDES:
        if guide.label.casefold() == normalized:
            return guide
    # Preserve support for custom purposes in the standalone CLI.
    general = PURPOSE_GUIDES[-1]
    return PurposeGuide(
        purpose.strip(), general.recipient,
        f"Write specifically for the requested purpose: {purpose.strip()}.",
        general.subject, general.salutation,
        "Close in a way that serves the requested purpose; do not assume a financial request is needed.",
        general.avoid,
    )
