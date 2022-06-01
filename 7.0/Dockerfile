FROM debian:stable
MAINTAINER Michael Telahun Makonnen @mtelahun

ENV ODOO_VERSION 7.0

#
# Configure APT packages and upgrade
#
RUN apt-get update
RUN apt-get upgrade -y

#
# Locale setup (if not set, PostgreSQL creates the database in SQL_ASCII)
#
RUN echo "locales locales/locales_to_be_generated multiselect en_US.UTF-8 UTF-8" | debconf-set-selections &&\
    echo "locales locales/default_environment_locale select en_US.UTF-8" | debconf-set-selections
RUN apt-get install debconf locales
RUN locale-gen en_US.UTF-8
ENV LC_ALL en_US.UTF-8

#
# Install PostgreSQL and Supervisor
#
RUN apt-get install --allow-unauthenticated -y supervisor postgresql python2.7 curl

#
# Install some OpenERP build deps
#
RUN apt-get install -y build-essential pkg-config libpython2.7-dev \
	libxml2-dev libxslt1-dev lzma-dev libpq-dev \
	libsasl2-dev libldap2-dev libssl-dev

RUN curl https://bootstrap.pypa.io/pip/2.7/get-pip.py -o get-pip.py
RUN python2.7 get-pip.py

# Install some deps, lessc and less-plugin-clean-css, and wkhtmltopdf
RUN set -x; \
        apt-get install -y --no-install-recommends \
            ca-certificates \
            git \
            node-less \
        && curl -o wkhtmltox.deb -SL https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.1/wkhtmltox-0.12.1_linux-wheezy-amd64.deb \
        && echo '07d397b32f91722de683e8777df2ddd6c49662c2 wkhtmltox.deb' | sha1sum -c - \
        && dpkg --force-depends -i wkhtmltox.deb \
        && apt-get -y install -f --no-install-recommends \
        && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false -o APT::AutoRemove::SuggestsImportant=false npm \
        && rm -rf /var/lib/apt/lists/* wkhtmltox.deb \
        && pip install psycogreen==1.0

#
# PostgreSQL: add user openerp and fix permissions
#
RUN /etc/init.d/postgresql start && su postgres -c "createuser -s openerp"
RUN chown -R postgres.postgres /var/lib/postgresql
VOLUME  ["/var/lib/postgresql"]

ADD requirements.txt requirements.txt
COPY tarballs/PyXML-0.8.4.tar.gz PyXML-0.8.4.tar.gz
RUN echo "#define HAVE_MEMMOVE 1" >> /usr/include/python2.7/pyconfig.h
RUN pip install PyXML-0.8.4.tar.gz
RUN pip install install -r requirements.txt

RUN pip install Python-Chart mako mock==1.1.0 psutil==2.1.3 simplejson unittest2 xlrd
RUN apt-get update
RUN apt-get install -y python3 python3-distutils
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
RUN python3 get-pip.py
RUN pip3 install jsonrpc2 daemonize
RUN apt-get install -y libreoffice-writer libreoffice-calc xvfb openjdk-17-jre
RUN apt-get install -y libreoffice-script-provider-python

RUN mkdir /opt/aeroo
RUN git clone https://github.com/aeroo/aeroolib.git /opt/aeroo/aeroolib
RUN git clone https://github.com/aeroo/aeroo_docs.git /opt/aeroo/aeroo_docs

WORKDIR /opt/aeroo/aeroolib
RUN python2.7 setup.py install

RUN echo Y | python3 /opt/aeroo/aeroo_docs/aeroo-docs start -c /etc/aeroo-docs.conf
RUN ln -s /opt/aeroo/aeroo_docs/aeroo-docs /etc/init.d/aeroo-docs

RUN update-rc.d aeroo-docs defaults
RUN echo 'start aeroo-docs service'
RUN service aeroo-docs start

RUN echo '#!/bin/sh' > /etc/init.d/office
RUN echo '/usr/bin/soffice --nologo --nofirststartwizard --headless --norestore --invisible "--accept=socket,host=localhost,port=8100,tcpNoDelay=1;urp;" &' >> /etc/init.d/office

RUN chmod +x /etc/init.d/office
RUN update-rc.d office defaults
RUN /etc/init.d/office restart

WORKDIR /

#
# Clean
#
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/
RUN rm requirements.txt PyXML-0.8.4.tar.gz

#
# Supervisor setup
#
ADD etc/supervisor/conf.d/10_postgresql.conf /etc/supervisor/conf.d/10_postgresql.conf
ADD etc/supervisor/conf.d/20_openerp.conf /etc/supervisor/conf.d/20_openerp.conf
ADD etc/supervisor/conf.d/30_openerp_jobrunner.conf /etc/supervisor/conf.d/30_openerp_jobrunner.conf

#
# Create OpenERP user
#
RUN adduser --system --home=/opt/openerp --group openerp

#
# Copy OpenERP src files
#
RUN mkdir -p /opt/openerp/log /opt/openerp/etc
ADD src/ /opt/openerp/src/
ADD etc/openerp-server.conf /opt/openerp/etc/openerp-server.conf
RUN chown -R openerp:openerp /opt/openerp

EXPOSE 8069
CMD ["/usr/bin/supervisord", "-n"]

