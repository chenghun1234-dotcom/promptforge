import os
import re
import time
from datetime import datetime, timezone

from groq import Groq


DEFAULT_MODEL = "llama-3.3-70b-versatile"


def get_trending_topics() -> list[str]:
	return ["Cyberpunk Cyberwear for Zepeto", "Isometric 3D Room for Roblox"]


def generate_pro_post(client: Groq, topic: str) -> str:
	prompt = f"""
Create a professional AI prompt guide for: '{topic}'.
The target audience is pro creators selling digital assets.
Write in English. Include:
1. Title (SEO optimized)
2. Pro Prompt (Main prompt + Negative prompt)
3. Technical Settings (Sampler, CFG, Steps)
4. Monetization Tip (How to sell this asset)
Output format: Markdown with a Frontmatter.
Frontmatter fields:
- title (string)
- description (string)
- date (ISO 8601 string)
- tags (array of strings)
- model (string)
- prompt (string)
- negativePrompt (string)
- sampler (string)
- cfg (number)
- steps (number)
- monetizationTip (string)
"""

	chat_completion = client.chat.completions.create(
		model=os.environ.get("GROQ_MODEL", DEFAULT_MODEL),
		messages=[{"role": "user", "content": prompt}],
		temperature=float(os.environ.get("GROQ_TEMPERATURE", "0.6")),
	)
	return chat_completion.choices[0].message.content


def slugify(value: str) -> str:
	value = value.strip().lower()
	value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
	value = re.sub(r"[\s_-]+", "-", value)
	value = re.sub(r"^-+|-+$", "", value)
	return value or "untitled"


def ensure_frontmatter(content: str, topic: str, model: str) -> str:
	if content.lstrip().startswith("---"):
		return content

	def escape(value: str) -> str:
		return value.replace("\\", "\\\\").replace('"', '\\"')

	title = topic.strip() or "PromptForge"
	now = datetime.now(timezone.utc).isoformat()
	fm = (
		"---\n"
		f'title: "{escape(title)}"\n'
		f'description: "Forged prompt guide for {escape(title)}"\n'
		f'date: "{now}"\n'
		"tags: []\n"
		f'model: "{model}"\n'
		"---\n\n"
	)
	return fm + content


def save_to_content(content: str, filename: str) -> str:
	project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	path = os.path.join(project_root, "src", "content", "prompts", f"{filename}.md")
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "w", encoding="utf-8", newline="\n") as f:
		f.write(content)
	return path


def main() -> None:
	api_key = os.environ.get("GROQ_API_KEY")
	if not api_key:
		raise RuntimeError("GROQ_API_KEY is not set")

	sleep_seconds = float(os.environ.get("GROQ_SLEEP_SECONDS", "10"))
	model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
	client = Groq(api_key=api_key)

	topics = get_trending_topics()
	for index, topic in enumerate(topics):
		slug = slugify(topic)
		post_content = generate_pro_post(client, topic)
		post_content = ensure_frontmatter(post_content, topic, model)
		output_path = save_to_content(post_content, slug)
		print(f"Successfully forged: {output_path}")
		if index != len(topics) - 1:
			time.sleep(sleep_seconds)


if __name__ == "__main__":
	main()
