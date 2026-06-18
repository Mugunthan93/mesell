#!/usr/bin/env bash
# MeeSell localhost monitoring statusline. Fast (/dev/tcp port checks + pgrep). No HTTP.
cat >/dev/null 2>&1   # consume Claude's stdin JSON
MESELL=/Users/mugunthansrinivasan/Project/mesell
G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; D=$'\033[2m'; X=$'\033[0m'
up(){ (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && { exec 3>&- 3<&-; return 0; }; return 1; }
ok(){ printf "%s%s%s" "$G" "$1" "$X"; }; bad(){ printf "%s%s%s" "$R" "$1" "$X"; }
up 8000 && BE=$(ok "BE✓") || BE=$(bad "BE✗")
up 4200 && SH=$(ok "SH✓") || SH=$(bad "SH✗")
n=0; for p in 4201 4202 4203 4204 4205 4206; do up $p && n=$((n+1)); done
[ $n -eq 6 ] && MFE=$(ok "MFE $n/6") || MFE=$(bad "MFE $n/6")
pgrep -f "celery.*worker" >/dev/null 2>&1 && CEL=$(ok "CEL✓") || CEL=$(bad "CEL✗")
m=$(pgrep -f "tail -n0 -F.*backend.log" 2>/dev/null | wc -l | tr -d ' ')
[ "$m" = "2" ] && MON=$(ok "mon $m/2") || { [ "$m" = "0" ] && MON=$(bad "mon $m/2") || MON=$(printf "%smon %s/2%s" "$Y" "$m" "$X"); }
BR=$(git -C "$MESELL" rev-parse --short HEAD 2>/dev/null)
printf "⬢ MeeSell │ %s %s %s %s │ %s │ %sdevelop %s%s" "$BE" "$SH" "$MFE" "$CEL" "$MON" "$D" "$BR" "$X"
