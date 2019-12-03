#!/bin/bash
# <bitbar.title>Multiple Jenkins Status</bitbar.title>
# <bitbar.desc>Check status of multiple Jenkins projects</bitbar.desc>
# <bitbar.author>Nocolas Roger</bitbar.author>
# <bitbar.author.github>nicolasroger17</bitbar.author.github>
# <bitbar.version>1</bitbar.version>

SCHEMA="https"
BASE_URL="jenkins.portaal.rabobank.nl"
USER="trietsr"
TOKEN="11ebea9c71fbfefebeed517193154e2e95" #prefer tokens to passwords (passwords can still be used here), get it from $SCHEMA://$BASE_URL/user/$USER/configure -> Show API Token
PROJECTS=("rbo_user_profile_and_preferences_quality")

function displaytime {
  local T=$1/1000
  local D=$((T/60/60/24))
  local H=$((T/60/60%24))
  local M=$((T/60%60))
  local S=$((T%60))
  local output=""

  if [[ $D -gt 0  || $H -gt 0 || $M -gt 10 ]]
  then
    output+=">10mn"
  else
    output+="${M}mn ${S}s"
  fi

  echo "${output} ago"
}

# beginning of display
echo "Jenkins Status"
echo "---"

for project in "${PROJECTS[@]}"
do
  output="${project}: "
  url="${SCHEMA}://${USER}:${TOKEN}@${BASE_URL}/job/${project// /'%20'}/lastBuild/api/json?pretty=true"
  query=$(curl --insecure --silent "${url}")

  success=$(echo "${query}" | grep '"result"' | awk '{print $3}') # grep the "result" line

  if [[ $success == *"SUCCESS"* ]]
  then
    output+='🔵 '
  else
    output+='🔴 '
  fi

  timestamp=$(echo "${query}" | grep "timestamp" | awk '{print $3}') # grep the "timestamp" line
  timestamp=${timestamp%?} # remove the trailing ','
  currentTime=$(($(date +'%s * 1000 + %-N / 1000000'))) # generate a timestamp
  output+=" $(displaytime $(( currentTime - timestamp )))"
  echo "${output}"
done