# Clash Detection Bake

Primary Python based clash detection extension that generates USD Layers containing clash meshes and intersection outlines.


``omni.physx.clashdetection.bake`` only supports **time sampled animated layers**.

    - Any animation created through the use of ``omni.anim.curve.core`` must be baked to a time-sampled layer.
    - The original animation curves must be deleted or the corresponding PushGraph must be deleted or de-activated.
    - If deleting animation curves data is not feasible, disabling the ``omni.anim.curve.core`` extension while generating and viewing clash backed layer can avoid such issues.
    - Failure to do any of the above may cause clash faces not to be animated correctly with the timeline position.

For full documentation, please see the omni.physx.clashdetection.bundle extension.