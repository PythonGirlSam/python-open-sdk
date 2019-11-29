import os
from oslo_config import cfg
import logging.config as log_cfg


def register_conf_file(config_file=None):
    if not config_file:
        config_file = os.path.join('/etc/open-sdk/',
                                   'open-sdk.cfg')
        if not os.path.exists(config_file):
            config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                       'open-sdk.cfg')
    
    # parse conf file
    cfg.CONF(['--config-file', config_file], project='open-sdk')

    opts = [
        cfg.StrOpt('pets_api_version',
                   default="v1",
                   help='Pets API.')

    ]

    defaults = [cfg.URIOpt('api_uri',
                schemes=["https", "http"],
                default='http://0.0.0.0:8000',
                help='Host url for api'),
                cfg.StrOpt('log_config_location',
                default=os.path.join(os.path.dirname(
                       os.path.dirname(__file__)), 'logger.config'),
                help='Log config file location')]

    api_versions = cfg.OptGroup(name='api_versions',
                                title='Product API options')
    cfg.CONF.register_group(api_versions)
    cfg.CONF.register_opts(opts, group=api_versions)
    cfg.CONF.register_opts(defaults)

    if not os.path.exists(cfg.CONF.log_config_location):
        logging_config = os.path.join(os.path.dirname(
            os.path.dirname(__file__)), 'logger.config')
    else:
        logging_config = cfg.CONF.log_config_location

    log_cfg.fileConfig(logging_config)
