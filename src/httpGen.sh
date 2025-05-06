#!/bin/bash

url="http://10.0.0.4"

while true; do
    sleep_time=$(awk -v min=0.2 -v max=0.8 'BEGIN{srand(); print int(min+rand()*(max-min+1))}')
    response=$(curl -s $url)
    echo "Response: $response"
    sleep $sleep_time
done

