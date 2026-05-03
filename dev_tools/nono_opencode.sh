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
  --read-file ~/.ssh/config \
  --read-file ~/.ssh/id_ed25519_github \
  --read-file ~/.ssh/id_ed25519_github.pub \
  --read-file ~/.ssh/id_ed25519_github-cert \
  --read-file ~/.ssh/id_ed25519_github-cert.pub \
  --read-file ~/.ssh/known_hosts \
  --read-file ~/.cargo/bin/nono \
  --allow-file /var/run/docker.sock \
  -- opencode
