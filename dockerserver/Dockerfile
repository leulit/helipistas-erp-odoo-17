FROM odoo:17.0

USER root

# Configuración persistente de locales y fuentes Unicode
RUN apt-get update && \
    apt-get install -y --no-install-recommends locales fonts-dejavu-core wget xfonts-75dpi xfonts-base && \
    echo "es_ES.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen es_ES.UTF-8 && \
    update-locale LANG=es_ES.UTF-8 LC_ALL=es_ES.UTF-8 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=es_ES.UTF-8
ENV LC_ALL=es_ES.UTF-8
ENV LANGUAGE=es_ES:es

RUN apt-get update && \
    apt-get remove -y wkhtmltopdf && \
    wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.5-1/wkhtmltox_0.12.5-1.stretch_amd64.deb -O /tmp/wkhtmltox.deb && \
    dpkg -i /tmp/wkhtmltox.deb || apt-get install -f -y && \
    rm /tmp/wkhtmltox.deb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    echo "wkhtmltopdf version instalada:" && \
    wkhtmltopdf --version


# Librerías Python adicionales
# pyOpenSSL/cryptography fijados: google-cloud-aiplatform sin techo de versión rompe el
# pyOpenSSL de apt (llama a OpenSSL_add_all_algorithms, eliminado de cryptography moderno);
# y cryptography>=39 rompe a su vez urllib3.contrib.pyopenssl (usa
# cryptography.hazmat.backends.openssl.x509, eliminado en cryptography 39). 23.0.0/38.0.4 es
# el único hueco verificado que cumple ambos lados. Visto en incidente de producción 2026-09-22.
# pycountry: lo pedía base_iso3166 (third-party-addons) y no estaba en esta imagen; alguien
# lo instaló a mano en el contenedor vivo sin tocar el Dockerfile, se perdió al recrearlo.
RUN pip install pypdf pyqrcode pyotp pypng schwifty==2024.4.0 xmlsig pycountry "google-cloud-aiplatform==1.165.1" "pyOpenSSL==23.0.0" "cryptography==38.0.4"

USER odoo
