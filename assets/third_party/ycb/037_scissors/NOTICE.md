# YCB 037 scissors asset notice

This directory contains the textured Google-scanner 16k model for YCB object
`037_scissors`, obtained from the [official YCB Object and Model Set site](https://ycb-benchmarks.s3.amazonaws.com/index.html).

The YCB dataset is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
Attribution: Berk C. Calli, Arjun Singh, Aaron Walsman, Siddhartha Srinivasa,
Pieter Abbeel, and Aaron M. Dollar, *The YCB Object and Model Set: Towards
Common Benchmarks for Manipulation Research* (2015).

For this reconstruction, the original OBJ geometry is converted into a USD
mesh, centered at its measured bounds, and the yellow/orange handle faces are
recolored blue to match the Appendix G reference image. The original scanned
texture remains unchanged. A simple hidden box collider is used for PhysX.
