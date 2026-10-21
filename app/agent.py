# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from google.cloud import firestore
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.genai import types

from .a2ui_utils import a2ui_callback




MODEL = "gemini-3.8-flash"
PROJECT_ID = "qwiklabs-gcp-03-d7d8c6f5a56e"
AGENT_ENGINE_ID = "5037711864696406016"
AGENT_ENGINE_RESOURCE = f"projects/358851345818/locations/us-central1/reasoningEngines/{AGENT_ENGINE_ID}"


# Initialize Firestore client with explicit project ID string
db = firestore.Client(project=PROJECT_ID)


def list_books(genre: str = "", max_results: int = 10) -> list[dict]:
    """Lists classic books from the catalog, optionally filtered by genre keyword.

    Args:
        genre: Optional genre keyword to filter books (e.g. 'Victorian', 'Gothic', 'Dystopian', 'Romance').
        max_results: Maximum number of books to return (default: 10).

    Returns:
        A list of book dictionaries containing title, author, year, genre, difficulty, themes, and synopsis.
    """
    books_ref = db.collection("classic_books")
    docs = books_ref.stream()
    
    results = []
    genre_lower = genre.strip().lower() if genre else ""
    for doc in docs:
        data = doc.to_dict()
        if genre_lower:
            book_genre = str(data.get("genre", "")).lower()
            book_themes = [str(t).lower() for t in data.get("themes", [])]
            if genre_lower not in book_genre and not any(genre_lower in t for t in book_themes):
                continue
        results.append(data)
        if len(results) >= max_results:
            break
            
    return results


def get_book_details(book_id: str) -> dict:
    """Gets detailed information and quotes for a specific classic book by ID or title slug.

    Args:
        book_id: The ID or slug of the book (e.g. 'pride-and-prejudice', 'frankenstein', 'crime-and-punishment', '1984', 'the-odyssey', 'the-great-gatsby').

    Returns:
        A dictionary containing full book metadata, synopsis, themes, and famous quotes.
    """
    clean_id = book_id.strip().lower().replace(" ", "-")
    doc_ref = db.collection("classic_books").document(clean_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    
    # Fallback search by title
    docs = db.collection("classic_books").stream()
    for d in docs:
        data = d.to_dict()
        if clean_id in str(data.get("title", "")).lower().replace(" ", "-"):
            return data
            
    return {"error": f"Book '{book_id}' not found in the classics catalog."}


def update_reading_list(user_id: str, book_title: str, status: str = "want_to_read", rating: int = 0, notes: str = "") -> dict:
    """Adds or updates a book in the user's personal reading list in Firestore.

    Args:
        user_id: The ID or username of the user.
        book_title: The title of the classic book.
        status: The reading status ('want_to_read', 'currently_reading', 'completed').
        rating: Optional rating from 1 to 5 (0 if unrated).
        notes: Personal reflection or notes about the book.

    Returns:
        A dictionary confirming the saved reading list entry.
    """
    doc_id = f"{user_id.strip().lower()}_{book_title.strip().lower().replace(' ', '_')}"
    entry = {
        "user_id": user_id,
        "book_title": book_title,
        "status": status,
        "rating": rating,
        "notes": notes,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    db.collection("user_reading_lists").document(doc_id).set(entry)
    return {"status": "success", "message": f"Updated '{book_title}' in {user_id}'s reading list with status '{status}'."}


def get_user_reading_list(user_id: str) -> list[dict]:
    """Retrieves all books and statuses from the user's personal reading list in Firestore.

    Args:
        user_id: The ID or username of the user.

    Returns:
        A list of reading list entries saved by the user.
    """
    entries = db.collection("user_reading_lists").where(filter=firestore.FieldFilter("user_id", "==", user_id)).stream()
    results = [entry.to_dict() for entry in entries]
    return results


import uuid
import requests
from google import genai
from google.cloud import storage


BUCKET_NAME = "classic-literature-companion-20218"
_genai_client = None
_storage_client = None

def _get_genai_client():
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")
    return _genai_client

def _get_storage_client():
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


def calculate_reading_pace(book_title_or_id: str, minutes_per_day: int = 30, reading_speed_wpm: int = 250) -> dict:
    """Calculates reading schedule, daily page goals, and days to finish a book.

    Args:
        book_title_or_id: Title or ID of the book to calculate pace for.
        minutes_per_day: Daily reading commitment in minutes (default: 30).
        reading_speed_wpm: Reader's reading speed in words per minute (default: 250).

    Returns:
        A dictionary containing estimated reading hours, total days, and daily pages target.
    """
    # Fetch page count from catalog if available
    details = get_book_details(book_title_or_id)
    pages = details.get("pages", 350) if isinstance(details, dict) and "pages" in details else 350
    title = details.get("title", book_title_or_id) if isinstance(details, dict) and "title" in details else book_title_or_id

    total_words = pages * 275
    effective_wpm = max(reading_speed_wpm, 50)
    effective_mins = max(minutes_per_day, 5)
    
    total_reading_minutes = total_words / effective_wpm
    total_days = max(1, round(total_reading_minutes / effective_mins))
    pages_per_day = round(pages / total_days, 1)
    
    return {
        "book": title,
        "page_count": pages,
        "estimated_total_hours": round(total_reading_minutes / 60, 1),
        "days_to_finish": total_days,
        "daily_reading_minutes": effective_mins,
        "pages_per_day": pages_per_day,
        "summary": f"Reading {effective_mins} mins/day at {effective_wpm} WPM, you will finish '{title}' ({pages} pages) in ~{total_days} days ({pages_per_day} pages/day)."
    }


def fetch_public_domain_passage(search_query: str) -> dict:
    """Searches and retrieves public domain book metadata, topics, and Gutenberg archive links.

    Args:
        search_query: Book title or author name to look up in the public domain archive.

    Returns:
        A dictionary containing book title, authors, subject tags, and archive links.
    """
    try:
        resp = requests.get(
            f"https://gutendex.com/books?search={requests.utils.quote(search_query)}",
            timeout=5
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                book = results[0]
                return {
                    "found": True,
                    "title": book.get("title"),
                    "authors": [a.get("name") for a in book.get("authors", [])],
                    "subjects": book.get("subjects", [])[:4],
                    "gutenberg_id": book.get("id"),
                    "download_count": book.get("download_count"),
                }
    except Exception as e:
        pass
    
    return {"found": False, "query": search_query, "message": f"Archived entry for '{search_query}' referenced."}


async def generate_book_illustration(
    prompt: str,
    tool_context: ToolContext,
    style: str = "vintage classic book illustration",
) -> dict:
    """Generates an illustration for a classic literature scene, character, or book cover, saves it as an artifact, and uploads to public Cloud Storage.

    Args:
        prompt: Description of the scene, character, or concept to illustrate (e.g. 'Victor Frankenstein standing before his creation on Mont Blanc', 'Elizabeth Bennet and Mr. Darcy at Pemberley estate').
        style: Artistic style (e.g. 'vintage classic book illustration', '19th century Victorian woodcut engraving', 'gothic oil painting').

    Returns:
        A dictionary containing the public Cloud Storage image URL, artifact filename, and display status.
    """
    full_prompt = f"{style}, {prompt}"
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=full_prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])
        )
        
        image_bytes = None
        mime_type = "image/jpeg"
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break
            if image_bytes:
                break
                
        if not image_bytes:
            return {"error": "Failed to generate image bytes."}

        ext = "jpg" if "jpeg" in mime_type or "jpg" in mime_type else "png"
        file_id = f"art_{uuid.uuid4().hex[:8]}.{ext}"

        # 1. Save artifact so it shows up in Playground's Artifacts panel
        if tool_context:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=file_id, artifact=artifact_part)

        # 2. Upload same bytes directly to public Cloud Storage bucket
        storage_client = _get_storage_client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_id)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{file_id}"
        return {
            "status": "success",
            "prompt": prompt,
            "style": style,
            "artifact_filename": file_id,
            "image_url": public_url,
            "display_markdown": f"![{prompt}]({public_url})",
        }
    except Exception as e:
        return {"error": f"Image generation failed: {str(e)}"}



def lookup_classic_poem(search_term: str, max_lines: int = 30) -> dict:
    """Fetches full-text classic poetry, sonnets, or stanzas from the free PoetryDB public API.

    Args:
        search_term: The title of the poem (e.g. 'Ozymandias', 'The Raven', 'Sonnet 18') or poet name (e.g. 'Emily Dickinson', 'Percy Bysshe Shelley', 'John Keats', 'William Blake').
        max_lines: Maximum number of poem lines to return (default: 30).

    Returns:
        A dictionary containing the poem title, poet author, total line count, and the poem lines.
    """
    url = f"https://poetrydb.org/title/{requests.utils.quote(search_term)}"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json() if resp.status_code == 200 else []
        
        if not isinstance(data, list) or not data or "status" in data:
            url = f"https://poetrydb.org/author/{requests.utils.quote(search_term)}"
            resp = requests.get(url, timeout=5)
            data = resp.json() if resp.status_code == 200 else []
            
        if isinstance(data, list) and len(data) > 0 and "title" in data[0]:
            poem = data[0]
            lines = poem.get("lines", [])
            truncated = len(lines) > max_lines
            return {
                "found": True,
                "title": poem.get("title"),
                "author": poem.get("author"),
                "total_lines": len(lines),
                "poem_text": "\n".join(lines[:max_lines]),
                "is_truncated": truncated,
            }
    except Exception as e:
        return {"found": False, "error": f"Failed to retrieve poem: {str(e)}"}
        
    return {"found": False, "message": f"No classic poem found for '{search_term}'."}


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback executed after each turn to extract and persist durable facts to Memory Bank."""
    await callback_context.add_session_to_memory()
    return None


def memory_bank_service_builder():
    """Builds VertexAiMemoryBankService pointed at the Agent Engine Memory Bank."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location="us-central1",
        agent_engine_id=AGENT_ENGINE_ID,
    )


try:
    from a2ui.schema.manager import A2uiSchemaManager
    from a2ui.basic_catalog.provider import BasicCatalog

    schema_manager = A2uiSchemaManager(
        version="0.8",
        catalogs=[BasicCatalog.get_config("0.8")],
    )

    instruction = schema_manager.generate_system_prompt(
        role_description=(
            "You are the Classic Literature Companion, an eloquent and knowledgeable literary concierge. "
            "You remember the user's stated reading preferences, favorite authors, themes, and notes across conversations "
            "and use them to personalize your recommendations. "
            "Help readers discover masterpieces, explore themes and literary analysis, check famous quotes, "
            "calculate reading pace goals, retrieve classic poetry, and manage their personal reading list. "
            "You have access to tools to browse and search classic books (`list_books`, `get_book_details`), "
            "manage user reading lists (`get_user_reading_list`, `update_reading_list`), "
            "calculate reading pace (`calculate_reading_pace`), search archives (`fetch_public_domain_passage`), "
            "retrieve poetry (`lookup_classic_poem`), generate illustrations (`generate_book_illustration`), "
            "and execute Python code in a safe sandbox."
        ),
        workflow_description="Analyze the request, call relevant tools to fetch information or perform actions, and return structured A2UI UI when appropriate.",
        ui_description=(
            "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
            "Never nest a Card inside a Card. "
            "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
            "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
            "nothing in adk web). "
            "You may include one Image component, but only when you have a public https "
            "URL for the image (for example the URL an image tool returns after uploading "
            "to a public bucket). Set the Image url to that exact https link, for example "
            "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
            "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
            "not have a public URL, add a short Text line noting the image instead. "
            "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
            "headings and emphasis. "
            "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
            "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
        ),
        include_schema=True,
        include_examples=True,
    )
except ImportError:
    from .a2ui_prompt import A2UI_INSTRUCTION
    instruction = A2UI_INSTRUCTION



root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        list_books,
        get_book_details,
        update_reading_list,
        get_user_reading_list,
        calculate_reading_pace,
        fetch_public_domain_passage,
        lookup_classic_poem,
        generate_book_illustration,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=AGENT_ENGINE_RESOURCE,
    ),
)

app = App(
    root_agent=root_agent,
    name="app",
)





