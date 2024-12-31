FROM alpine:latest

RUN apk update && apk add git openssh go python3 py3-click

WORKDIR /root

ENV PATH="/root/go/bin:$PATH"

RUN go install github.com/gittuf/gittuf@v0.8.0

RUN gittuf version

ADD example_deployments.py utils.py /root/  

ADD keys/roots /root/keys/roots
ADD keys/policy /root/keys/policy
ADD keys/people /root/keys/people