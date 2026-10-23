import os
from unittest.mock import Mock
from tempfile import TemporaryDirectory
from pathlib import Path
from PIL import Image

os.environ['DISCORD_TOKEN'] = 'test-placeholder'
os.environ['GOOGLE_TOKEN'] = 'test-placeholder'
import main
from keep_alive import create_app

main.client.models.generate_content = Mock(return_value=Mock(text='A red square.', parts=[1]))
for call, arg in [(main.summarize_text, 'hi'), (main.rewrite_text, 'hi'),
                  (main.get_chat_response, 'hi'), (main.define_word, 'hi')]:
    assert call(arg) == 'A red square.'
    assert main.client.models.generate_content.call_args.kwargs['model'] == 'gemma-4-26b-a4b-it'
with TemporaryDirectory() as directory:
    path = Path(directory) / 'test.png'
    Image.new('RGB', (64, 64), 'red').save(path)
    assert main.image_cap(path) == 'A red square.'
assert len(main.discord_text('x' * 3000)) <= 2000
assert all(main.bot.get_command(name) for name in
           ['caption', 'chat', 'define', 'rewrite', 'catchup', 'on', 'off', 'commands', 'about'])
assert not main.bot.intents.members and not main.bot.intents.presences
app = create_app(main.bot, main.MODEL).test_client()
assert app.get('/').status_code == 200
assert app.get('/healthz').status_code == 503
main.bot.is_ready = Mock(return_value=True)
assert app.get('/healthz').status_code == 200
main.client.close()
print('PASS: text/image SDK calls, command registration, message limits, and health endpoint')
