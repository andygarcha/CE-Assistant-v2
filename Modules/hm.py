"""
This module, named after my legendary friend ApolloTheOne (aka apollohm),
will house a bunch of random pieces of data that need to be accessed
across multiple files.
"""

from utils.icons import *  # noqa: F403
from utils.channels import *  # noqa: F403
from utils.game_utils import *  # noqa: F403
from utils.general_utils import *  # noqa: F403
from utils.time_utils import *  # noqa: F403

import logging

logger = logging.getLogger(__name__)

logger.warning("The 'hm.py' module is deprecated. Use the 'utils' package instead.")
