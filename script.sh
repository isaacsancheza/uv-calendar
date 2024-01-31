#!/usr/bin/env sh

image_tag=scraper
docker build -t $image_tag app

docker run --rm -it \
    -e BUCKET_NAME=$BUCKET_NAME \
    -e CALENDARS_BUCKET_NAME=$CALENDARS_BUCKET_NAME \
    -e AWS_DEFAULT_REGION=$REGION \
    -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
    -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN \
    $image_tag
