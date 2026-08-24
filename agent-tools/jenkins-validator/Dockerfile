# Jenkins declarative pipeline structure validator
# No setup wizard, no authentication, no CSRF crumb — local use only
#
# Build (once):
#   $CONTAINER build $TLS_FLAG -t jenkins-validator "$AGENT_TOOLS/jenkins-validator"
#
# Run on demand:
#   $CONTAINER run -d --rm --name jenkins-validator -p 8080:8080 jenkins-validator

FROM jenkins/jenkins:lts-jdk17

# Disable the setup wizard and authentication
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"

# Import the TLS cert chain the corporate proxy presents for updates.jenkins.io
# into the JVM trust store. openssl s_client outputs certs regardless of trust
# status, so this works even before the cert is trusted.
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/* \
    && openssl s_client -connect updates.jenkins.io:443 -showcerts </dev/null 2>/dev/null \
       | awk '/-----BEGIN CERTIFICATE-----/{n++; f="/tmp/chain-"n".pem"; out=1} out{print > f} /-----END CERTIFICATE-----/{out=0}' \
    && ls /tmp/chain-*.pem 2>/dev/null | while read f; do \
         keytool -import -noprompt -trustcacerts \
           -alias "proxy-$(basename "$f" .pem)" \
           -file "$f" -cacerts -storepass changeit 2>&1 || true; \
         rm "$f"; \
       done
USER jenkins

COPY init.groovy.d/disable-security.groovy \
     /usr/share/jenkins/ref/init.groovy.d/disable-security.groovy

# Install only the declarative pipeline plugin and its dependencies
RUN jenkins-plugin-cli --plugins pipeline-model-definition
