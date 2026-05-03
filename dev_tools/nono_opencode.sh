#!/usr/bin/env sh
nono run -v --log-file /tmp/nono.log --profile opencode \
  --allow-cwd \
  --allow /home/aria/.npm \
  --allow /home/aria/.config/npm \
  --allow /home/aria/.cache/uv \
  --allow /home/aria/.local/share/uv \
  --allow /tmp \
  --allow /home/aria/ai/models/llm/GGUF \
  --read /usr/lib/node_modules \
  --read /home/aria/.config/opencode/rules \
  --read-file ~/.cargo/bin/nono \
  --allow-file /var/run/docker.sock \
  -- opencode
