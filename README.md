# Tavlo

Tavlo is a Discord bot that captions images for accessibility and provides chat,
definitions, rewrites, conversation summaries, and web search using Gemma 4 26B.

[Visit Tavlo](https://www.tavlo.app/)

## Commands

| Command | What it does |
| --- | --- |
| `!!commands` or `!!command` | Show available commands. |
| `!!about` | Introduce Tavlo. |
| `!!on` / `!!off` | Enable or disable automatic image captions. |
| `!!caption` with an attached image | Describe the image. |
| `!!chat <message>` | Chat with Gemma, with web search available when useful. |
| `!!search <query>` or `!!web <query>` | Search the web and answer with source links. |
| `!!define <word>` | Define a word. |
| `!!rewrite <text>` | Rewrite text more constructively. |
| `!!catchup`, `!!catch_up`, or `!!Catch` | Summarize recent conversation from the past 12 hours. |

Command names are case-insensitive. Automatic captioning processes the first image
attachment in a message that does not begin with a command. Use `!!chat` to chat;
Tavlo does not respond to every ordinary channel message.

## Search

Gemma can choose to search during any AI command, including chat, definitions,
rewrites, summaries, and captions. `!!search` and `!!web` force an initial search.

```text
!!search SearXNG official documentation
!!web Python official documentation
!!chat Look up the latest Python release on the official website.
```

Search uses SearXNG and provides titles, snippets, and source links to Gemma.
Each answer can use up to two searches. Explicit search accepts queries of 2 to
300 characters, with a ten-second per-user cooldown. Source links are retained
when long answers are shortened for Discord. If Gemma is unavailable after a
search, Tavlo returns the retrieved source links.

Search results may be incomplete or inaccurate. Search queries are sent to public
search engines; avoid including private information in an explicit query.
