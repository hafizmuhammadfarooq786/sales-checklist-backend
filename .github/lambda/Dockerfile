# The image staging runs on AWS Lambda: the app image plus one file.
#
# Lambda does not speak HTTP to a container. The Lambda Web Adapter is an
# extension that waits for the app to answer on its port, then turns each
# Lambda event into an ordinary HTTP request to it. Nothing outside Lambda
# looks in /opt/extensions, so the app image itself is left as it is.
#
# The adapter comes from a copy kept in this repository's own registry (tag
# lambda-adapter-1.1.0), not from public.ecr.aws: GitHub's shared runners
# exhaust that registry's anonymous pull quota.
ARG APP_IMAGE
ARG ADAPTER_IMAGE
FROM ${ADAPTER_IMAGE} AS adapter
FROM ${APP_IMAGE}
COPY --from=adapter /lambda-adapter /opt/extensions/lambda-adapter
