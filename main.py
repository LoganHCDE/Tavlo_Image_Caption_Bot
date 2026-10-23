import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
from google.genai import errors as google_exceptions
from PIL import Image
from keep_alive import keep_alive
from web_search import generate_with_search
import datetime
from pathlib import Path

# --- Configuration and Setup ---
load_dotenv()
D_Token = os.getenv('DISCORD_TOKEN')
G_Token = os.getenv('GOOGLE_TOKEN') or os.getenv('GEMINI_API_KEY')
TEMP_DIR = Path(__file__).with_name('tmp')
MODEL = os.getenv('GEMMA_MODEL', 'gemma-4-26b-a4b-it')
if MODEL != 'gemma-4-26b-a4b-it':
    raise SystemExit('Only the approved free Gemma 4 26B model is permitted')

# --- Early check for essential tokens ---
if not D_Token:
    print("FATAL ERROR: DISCORD_TOKEN not found. Please check your .env file or environment variables.")
    raise SystemExit(1)
if not G_Token:
    print("FATAL ERROR: GOOGLE_TOKEN not found. Please check your .env file or environment variables.")
    raise SystemExit(1)

# --- Logging and Intents Setup ---
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
# Only message content is required; member and presence intents are unnecessary.

# --- Global Variables ---
auto_caption_enabled = True

# --- Bot Initialization ---
bot = commands.Bot(command_prefix='!!', intents=intents, case_insensitive=True,
                   allowed_mentions=discord.AllowedMentions.none())
client = genai.Client(api_key=G_Token, vertexai=False, http_options=types.HttpOptions(timeout=90000, base_url='https://generativelanguage.googleapis.com'))

def complete(contents):
    if isinstance(contents, list):
        text = '\n\n'.join(part for part in contents if isinstance(part, str))
        contents = [text] + [part for part in contents if not isinstance(part, str)]
    response = client.models.generate_content(
        model=MODEL, contents=contents,
        config=types.GenerateContentConfig(max_output_tokens=2000))
    if not response.text or not response.text.strip():
        raise ValueError('Model returned no text')
    return response.text.strip()

def generate(contents, *, force_query=None):
    return generate_with_search(complete, contents, force_query=force_query)

def discord_text(text):
    # Preserve retrieved source links when shortening answers for Discord.
    if len(text) <= 2000:
        return text
    if "\n\nSources:\n" in text:
        body, sources = text.rsplit("\n\nSources:\n", 1)
        suffix = "\n\nSources:\n" + sources[:1100]
        return body[:1997 - len(suffix)] + '...' + suffix
    return text[:1997] + '...'



# --- Helper Functions ---

def get_about_text():
    """Returns the bot's standard about message."""
    about_text = """Hi! I am Tavlo, the image_captioning bot. I will automatically create captions for any images posted to this server. You can say `!!off` to turn off automatic captions, and `!!on` to turn them back on. Say `!!commands` to see all the different commands I can perform."""
    return about_text

def get_bot_persona():
    """
    Creates a string that describes the bot's identity and capabilities.
    """
    current_time = datetime.datetime.now().strftime('%I:%M %p %Z on %A, %B %d, %Y')

    persona_prompt = f"""You are Tavlo, a helpful and friendly AI assistant integrated into a Discord bot. Your main purpose is to help users by automatically captioning images to make them more accessible.

Your capabilities are defined by the following commands:
- `!!on` / `!!off`: These commands toggle your primary function of automatic image captioning.
- `!!caption [Image]`: This allows users to request a caption for a specific image on-demand.
- `!!catchup`: You can summarize the last 12 hours of conversation in the channel.
- `!!define [word]`: You can provide dictionary-style definitions for words.
- `!!rewrite [text]`: You can rephrase a user's text to sound more positive and constructive.
- `!!search [query]`: Search the web and answer with sources. You may also search automatically during any AI command.
- `!!about`: This command provides a brief description of you.
- `!!commands`: This command lists all your available functions.

When chatting with a user, you should be aware of these abilities.If a user asks what you can do, you should refer to these commands. You are also aware that the current time is approximately {current_time}. You can use ` ` around a single word to highlight it.
"""
    return persona_prompt

def summarize_text(transcript: str) -> str:
    """
    Uses the Google AI to summarize a chat transcript.
    """
    print("--- Starting summarize_text ---")
    try:


        prompt = (
            "Please provide a concise, easy-to-read summary of the following chat transcript from a Discord server. "
            "The summary should be in bullet points, highlighting the main topics discussed, any decisions made, and any unresolved questions. "
            "Limit yourself to a few sentences, only write Summary: and then the rest of summary, No other text."
            "You can use ` ` around a single word to highlight it."
            "ignore any messages about the command !!catchup."
            "Focus on the key information and ignore casual chit-chat.\n\n"
            "TRANSCRIPT:\n"
            f"```\n{transcript}\n```"
        )

        response = generate(prompt)

        if not response:
            return "The AI's summary was blocked, likely due to safety filters on the content of the chat."

        return response.strip()

    except Exception as e:
        print(f"[DEBUG] ERROR: An unexpected error occurred in summarize_text: {e}")
        return "An unexpected error occurred while generating the summary."

def rewrite_text(original_text: str) -> str:
    """
    Uses the Google AI to rewrite a given text to be more positive.
    """
    print(f"--- Starting rewrite_text for: '{original_text[:50]}...' ---")
    try:


        prompt = (
            "Your task is to rewrite the following text to sound less aggresive, "
            "more polite, and more friendly/SFW, while preserving the original message's core intent. "
            "Focus on turning criticism into constructive feedback and frustration into polite inquiry."
            "respond only with the rewritten text.\n\n"
            f"ORIGINAL TEXT: \"{original_text}\"\n\n"
            "REWRITTEN TEXT:"
        )

        response = generate(prompt)

        if not response:
            return "The AI's response was blocked, likely due to safety filters. Please try rephrasing your original message."

        return response.strip()

    except Exception as e:
        print(f"[DEBUG] ERROR: An unexpected error occurred in rewrite_text: {e}")
        return "An unexpected error occurred while rewriting the text."

def get_chat_response(user_input: str) -> str:
    """
    Uses the Google Generative AI to generate a chat response.
    """
    print(f"--- Starting get_chat_response for: '{user_input[:50]}...' ---")
    try:


        prompt = (f"{get_bot_persona()}\n\n"
          f"--- End of Persona ---\n\n"
          f"provide a helpful, funny and friendly response to the user's message."
          f"You can provide responses unrelated to your persona/purpose. You don't need to tell the user your purpose or capabilites unless they ask.\n\n"
          f"USER'S MESSAGE: \"{user_input}\"\n\n"
          f"YOUR RESPONSE:")

        response = generate(prompt)
        return response

    except google_exceptions.APIError as e:
        print(f"[DEBUG] ERROR: A Google API call error occurred: {e}")
        return "Sorry, I had a problem talking to my AI brain. Please try again later."
    except Exception as e:
        print(f"[DEBUG] ERROR: An unexpected error occurred in get_chat_response: {e}")
        return "An unexpected error occurred. I've logged the issue."

def define_word(word: str) -> str:
    """
    Uses the Google Generative AI to get a definition for a given word.
    """
    print(f"--- Starting define_word for: '{word}' ---")
    try:


        prompt = (f"Please provide a concise, dictionary-style definition for the following word: '{word}'. "
                  "If the word is slang, an acronym, or not a standard word, please clarify that in the definition. "
                  "If you cannot define it, simply state that a definition could not be found." "If it is not a word and instead a bunch of text, say that is the reason you can't provide a definition")

        response = generate(prompt)
        return response

    except google_exceptions.APIError as e:
        print(f"[DEBUG] ERROR: A Google API call error occurred: {e}")
        return "Sorry, there was a problem communicating with the AI model provider."
    except Exception as e:
        print(f"[DEBUG] ERROR: An unexpected error occurred in define_word: {e}")
        return f"An unexpected error occurred while trying to define the word."

def commands_list():
    """Returns a list of all available commands as a single text message."""
    command_text = """Here's what I can do:
`!!commands` - Shows this list of commands
`!!about` - Learn more about me
`!!on` / `!!off` - Toggle automatic image captioning.
`!!caption [Image]` - Captions the attached image.
`!!catchup` - Summarizes the last 12 hours of chat.
`!!define [word]` - Defines a word.
`!!rewrite [text]` - Rewrites your text to be more positive.
`!!chat [text]` - Chat with me; I can search the web when useful.
`!!search [query]` / `!!web [query]` - Search the web and answer with sources.
Search is also available automatically in other AI commands."""
    return command_text

def image_cap(image_path):
    """Generates a caption for a given image file."""
    print("--- Starting image_cap ---")
    try:


        with Image.open(image_path) as source:
            source.seek(0)
            img = source.convert("RGB")
            img.thumbnail((2048, 2048))

        guidelines = """
        Your primary goal is to generate a concise, descriptive, and objective caption for an image, specifically for visually impaired users.
        Focus on what is visually present in the image.
        - Describe the main subject(s) clearly.
        - Mention key objects and their arrangement.
        - Briefly describe the setting or background.
        - Note any prominent colors or lighting if they are important to the context.
        - Describe any actions or interactions taking place.
        - If there is text, transcribe it.
        Avoid making assumptions or interpreting emotions, intentions, or events that are not explicitly visible.
        """

        prompt = (f"{guidelines}\n\n"
                  "Using the guidelines provided, caption this image for people who are hard of seeing. "
                  "Only respond with the caption. Limit yourself to a few sentences.")

        response = generate([prompt, img])
        return response

    except FileNotFoundError:
        return "Error: Could not find the image file to process."
    except google_exceptions.APIError as e:
        print(f"[DEBUG] ERROR: A Google API call error occurred: {e}")
        return "Sorry, there was a problem with the AI model provider."
    except Exception as e:
        print(f"[DEBUG] ERROR: An unexpected error occurred in image_cap: {e}")
        return "Image captioning is temporarily unavailable. Please try again later."

# --- Bot Events ---

@bot.event
async def on_ready():
    """Event that fires when the bot is logged in and ready."""
    print('------')
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('Bot is ready to receive commands.')
    print('------')

@bot.event
async def on_message(message):
    """Event that fires on every message."""
    if message.author.bot:
        return

    if auto_caption_enabled and message.attachments and not message.content.startswith(bot.command_prefix):
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                processing_message = await message.channel.send("The Caption bot is thinking...")
                temp_image_path = str(TEMP_DIR / f"{attachment.id}.image")
                try:
                    await attachment.save(temp_image_path)
                    caption = await bot.loop.run_in_executor(None, image_cap, temp_image_path)
                    await processing_message.edit(content=discord_text(caption))
                except Exception as e:
                    await processing_message.edit(content="Image captioning is temporarily unavailable. Please try again later.")
                    print(f"Error in on_message: {e}")
                finally:
                    if os.path.exists(temp_image_path):
                        os.remove(temp_image_path)
                break

    await bot.process_commands(message)

# --- Bot Commands (omitted for brevity, they are unchanged) ---
@bot.command(name='commands', aliases=['command'])
async def commands_command(ctx):
    """Sends a list of all available commands."""
    await ctx.send(commands_list())

@bot.command(name='search', aliases=['web'])
@commands.cooldown(1, 10, commands.BucketType.user)
async def search_command(ctx, *, query: str):
    """Search the public web, then have Gemma answer with source links."""
    if not 2 <= len(query.strip()) <= 300:
        await ctx.send('Please use a search query of 2 to 300 characters.')
        return
    async with ctx.typing():
        try:
            import functools
            answer = await bot.loop.run_in_executor(None, functools.partial(
                generate, 'Answer this search question concisely using the retrieved evidence: ' + query,
                force_query=query))
            await ctx.send(discord_text(answer))
        except Exception as exc:
            logging.warning('Search command failed (%s)', type(exc).__name__)
            await ctx.send('Search is temporarily unavailable. Please try again later.')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f'Please wait {error.retry_after:.0f} seconds before searching again.')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'Missing input. See `!!commands` for usage.')
    elif not isinstance(error, commands.CommandNotFound):
        logging.warning('Command failed (%s)', type(error).__name__)
        await ctx.send('That command could not be completed. Please try again.')


@bot.command(name='define')
async def define_command(ctx, *, word: str):
    """Provides a definition for a given word using an AI model."""
    processing_message = await ctx.send(f"Looking up the definition for **{word}**...")
    definition = await bot.loop.run_in_executor(None, define_word, word)
    await processing_message.edit(content=discord_text(definition))

@bot.command(name='chat')
async def chat_command(ctx, *, text: str):
    """Allows users to have a conversation with the AI model."""
    async with ctx.typing():
        response_text = await bot.loop.run_in_executor(None, get_chat_response, text)
        await ctx.send(discord_text(response_text))

@bot.command(name='rewrite')
async def rewrite_command(ctx, *, text: str):
    """Rewrites the user's text to be more positive."""
    async with ctx.typing():
        rewritten_text = await bot.loop.run_in_executor(None, rewrite_text, text)
        if not rewritten_text or not rewritten_text.strip():
            await ctx.send("Sorry, the AI returned an empty response. Please try again.")
            return
        response_message = f"**Original:**\n> {text}\n\n**Rewritten:**\n> {rewritten_text}"
        await ctx.send(discord_text(response_message))

@bot.command(name='caption')
async def caption_command(ctx):
    """Captions an image attached to the command message."""
    if not ctx.message.attachments:
        await ctx.send("Please attach an image to your message to use the `!!caption` command.")
        return

    attachment = ctx.message.attachments[0]
    if not attachment.content_type or not attachment.content_type.startswith('image/'):
        await ctx.send("The attached file does not appear to be an image.")
        return

    processing_message = await ctx.send("Analyzing image to create a caption...")
    temp_image_path = str(TEMP_DIR / f"{attachment.id}.image")
    try:
        await attachment.save(temp_image_path)
        caption = await bot.loop.run_in_executor(None, image_cap, temp_image_path)
        await processing_message.edit(content=discord_text(caption))
    except Exception as e:
        await processing_message.edit(content="Sorry, an error occurred while processing the image.")
        print(f"Error in !!caption command: {e}")
    finally:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)

@bot.command(name='catchup', aliases=['catch_up', 'Catch'])
async def catch_up_command(ctx):
    """Summarizes the last 12 hours of conversation in the channel."""
    try:
        processing_message = await ctx.send("Catching up on the last 12 hours...")
        twelve_hours_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=12)
        messages = [msg async for msg in ctx.channel.history(limit=1000, after=twelve_hours_ago, oldest_first=True)]

        if not messages:
            await processing_message.edit(content="It's been quiet! No new messages in the last 12 hours.")
            return

        transcript = "\n".join(
            f"[{msg.created_at.strftime('%H:%M')}] {msg.author.display_name}: {msg.clean_content}"
            for msg in messages if not msg.author.bot
        )

        summary = await bot.loop.run_in_executor(None, summarize_text, transcript[:100000])

        await processing_message.edit(content=f"**Here's a catch-up on the last 12 hours:**")

        if len(summary) > 2000:
            for i in range(0, len(summary), 2000):
                await ctx.send(summary[i:i+2000])
        else:
            await ctx.send(summary)

    except discord.errors.Forbidden:
        await processing_message.edit(content="Error: I don't have the 'Read Message History' permission in this channel.")
    except Exception as e:
        await processing_message.edit(content="A critical error occurred while trying to catch up.")
        print(f"Error in !!catchup command: {e}")

@bot.command(name='on')
async def turn_on_auto_caption(ctx):
    """Turns on automatic image captioning."""
    global auto_caption_enabled
    auto_caption_enabled = True
    await ctx.send("Automatic Captioning is now **ON**.")

@bot.command(name='off')
async def turn_off_auto_caption(ctx):
    """Turns off automatic image captioning."""
    global auto_caption_enabled
    auto_caption_enabled = False
    await ctx.send("Automatic Captioning is now **OFF**.")

@bot.command(name='about')
async def about_command(ctx):
    """Sends a message with information about the bot."""
    await ctx.send(get_about_text())


@bot.event
async def on_guild_join(guild: discord.Guild):
    """Sends a welcome message when the bot joins a new server."""
    print(f"Joined a new server: {guild.name} (ID: {guild.id})")
    welcome_message = get_about_text()
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            try:
                await channel.send(welcome_message)
                print(f"Sent welcome message to #{channel.name} in {guild.name}")
                break
            except Exception as e:
                print(f"Failed to send welcome message to #{channel.name}: {e}")

# --- Bot Startup ---
if __name__ == '__main__':
    TEMP_DIR.mkdir(exist_ok=True)
    keep_alive(bot, MODEL)
    bot.run(D_Token, log_handler=handler, log_level=logging.INFO)
