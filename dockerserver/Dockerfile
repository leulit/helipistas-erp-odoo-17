FROM odoo:17.0

USER root

# Configuración persistente de locales y fuentes Unicode
RUN apt-get update && \
    apt-get install -y --no-install-recommends locales fonts-dejavu-core && \
    echo "es_ES.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen es_ES.UTF-8 && \
    update-locale LANG=es_ES.UTF-8 LC_ALL=es_ES.UTF-8 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=es_ES.UTF-8
ENV LC_ALL=es_ES.UTF-8
ENV LANGUAGE=es_ES:es

# Librerías Python adicionales
RUN pip install pypdf pyqrcode pyotp pypng

USER odoo

