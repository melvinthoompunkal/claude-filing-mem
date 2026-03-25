import os
import json
from pathlib import Path
from datetime import datetime
from mcp.server.fastmcp import FastMCP
import anthropic
from dotenv import load_dotenv


load_dotenv()


mcp = FastMCP("claude-filing-mem")

MEMORY_DIR = Path.home() / ".claude-filing-mem"
CATEGORIES = ["projects", "homework", "personal", "work", "research", "other"]

def ensure_dirs():
    for cat in CATEGORIES:
        (MEMORY_DIR / cat).mkdir(parents=True, exist_ok=True)

@mcp.tool()
def save_memory(conversation: str) -> str:
    """Analyze a conversation and save it to the appropriate category folder."""
    ensure_dirs()
    
    try:
        client = anthropic.Anthropic()
        
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""Analyze this conversation and return ONLY a JSON object with these fields:
- category: one of {CATEGORIES}
- title: short filename (no spaces, use hyphens, no .md extension)
- summary: 2-3 sentence compressed summary of what's important to remember

Conversation:
{conversation}

Return ONLY the JSON, no other text."""
            }]
        )
        
        raw = response.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        
        category = data.get("category", "other")
        if category not in CATEGORIES:
            category = "other"
            
        title = data.get("title", "untitled")
        summary = data.get("summary", conversation[:200])
        
        filename = f"{title}-{datetime.now().strftime('%Y%m%d')}.md"
        filepath = MEMORY_DIR / category / filename
        
        with open(filepath, "w") as f:
            f.write(f"# {title}\n")
            f.write(f"*Saved: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
            f.write(summary)
        
        return f"Saved to {category}/{filename}"
    
    except json.JSONDecodeError:
        # Fallback: save raw to other/
        filename = f"untitled-{datetime.now().strftime('%Y%m%d%H%M')}.md"
        filepath = MEMORY_DIR / "other" / filename
        with open(filepath, "w") as f:
            f.write(f"# Untitled\n")
            f.write(f"*Saved: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
            f.write(conversation[:500])
        return f"JSON parse failed, saved raw to other/{filename}"
    
    except Exception as e:
        return f"Error saving memory: {str(e)}"

@mcp.tool()
def list_memories(category: str = "") -> str:
    """List memories in a category, or all categories if none specified."""
    ensure_dirs()
    
    if category and category in CATEGORIES:
        cats = [category]
    else:
        cats = CATEGORIES
    
    result = []
    for cat in cats:
        files = list((MEMORY_DIR / cat).glob("*.md"))
        if files:
            result.append(f"[{cat}]")
            for f in files:
                result.append(f"  - {f.stem}")
    
    return "\n".join(result) if result else "No memories saved yet."

@mcp.tool()
def load_memory(category: str, filename: str = "") -> str:
    """Load a specific memory file or all memories in a category."""
    ensure_dirs()
    
    if filename:
        path = MEMORY_DIR / category / f"{filename}.md"
        if path.exists():
            return path.read_text()
        return f"File not found: {category}/{filename}"
    
    files = list((MEMORY_DIR / category).glob("*.md"))
    if not files:
        return f"No memories in {category}"
    
    return "\n\n---\n\n".join(f.read_text() for f in files)

@mcp.tool()
def delete_memory(category: str, filename: str) -> str:
    """Delete a specific memory file."""
    path = MEMORY_DIR / category / f"{filename}.md"
    if path.exists():
        path.unlink()
        return f"Deleted {category}/{filename}"
    return f"File not found: {category}/{filename}"


def setup():
    import subprocess
    subprocess.run(["claude", "mcp", "add", "claude-filing-mem", "claude-filing-mem"])
    print("✓ claude-filing-mem added to Claude Code")
    print("Remember to set ANTHROPIC_API_KEY in your .env file")

def main():
    mcp.run()

if __name__ == "__main__":
    main()