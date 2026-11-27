"""Sequential fresh cases; each native invocation retains its bounded timeout."""
import sys
from .run import main
for part in sys.argv[1:]:
 sys.argv=[sys.argv[0],part]
 main()
