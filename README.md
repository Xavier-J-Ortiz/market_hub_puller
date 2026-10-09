# Market Hub Puller v2

The first attempt at creating the market hub puller I did not think things
through the best way possible. I had created a working design, but also put in a
lot of work in terms of the data parsing. Though very informative and helped me
understand how this is done, I also could have used existing libraries and
housed this data as a database, using the existing functions that are well known
in SQL to yield the data that is of interest to me.

This made the code quite convoluted and difficult to read.

This second pass, am planning on simplifying the logic, and leveraging libraries
that are data centric, maybe even SQL centric, to streamline the workflow, and
allow an easier to understand and read codebase.
