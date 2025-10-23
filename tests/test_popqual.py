# Test get_popquals method of suggestbot.utilities.popqual
import sys
import os

# Add the parent directory to the Python path
# Use this line only if your want to test the script directly from the current path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import suggestbot.utilities.popqual as sup
import logging

logging.basicConfig(level=logging.INFO)


# pagelist = [
#     "Barack Obama",
#     "Ara Parseghian",
#     "Clarence Darrow",
#     "Andre Dawson",
#     "2004 Chicago Bears season",
#     "Jack O'Callahan",
#     "Switchcraft",
# ]

pagelist = [
    "إيلون ماسك",
    "المغرب",
    "فاس",
    "مرآة التيار",
]

for pq_info in sup.get_popquals("ar", pagelist):
    print(pq_info)
