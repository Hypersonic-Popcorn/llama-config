#!/usr/bin/env sh
nono run -v --log-file /tmp/nono.log --profile opencode \
  --allow-cwd \
  --read "$HOME/.local/share/Larian Studios/Baldur's Gate 3" \
  --read-file ./dev_tools/nono_opencode.sh \
  --read-file ~/.cargo/bin/nono \
  --allow /home/aria/.cache/uv \
  --allow /home/aria/.local/share/uv \
  -- opencode
