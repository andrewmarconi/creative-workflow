TV Spots App (cw.tvspots)
=========================

The ``cw.tvspots`` Django app manages TV spot production workflows including
versions, storyboards, and market adaptations.

Models
------

Django ORM models for TVSpot, TVSpotVersion, StoryboardJob, and AdaptationMarket.

.. automodule:: cw.tvspots.models
   :members:
   :undoc-members:
   :show-inheritance:

Tasks
-----

Celery tasks for storyboard generation and market adaptation.

.. automodule:: cw.tvspots.tasks
   :members:
   :undoc-members:
   :show-inheritance:

Admin
-----

Django Unfold admin configuration for the TV spots app.

.. automodule:: cw.tvspots.admin
   :members:
   :undoc-members:
   :show-inheritance:
