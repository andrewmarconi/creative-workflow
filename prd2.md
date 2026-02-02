## Components

Docker Compose file with:

- Postgres 17.x (exposing port 5435 instead of 5432)
- Valkey (alternative to Redis)

Django App:

- Django 6.x
- Django-RQ
- Jazzmin Admin

Existing Python Modules for:

- LoRAManager
- Models/base
- Models/flux
- Models/qwen
- Models/flux
- Prompt/Enhancer

Django Models:

- DiffusionModels (based on the presets.json)
- LoraModels  (based on the presents.json)
- Prompts - include source and enhanced prompt fields
- DiffusionJobs - track status, parameters, and results of diffusion tasks

## Workflow

In the admin, user can create and manage DiffusionModels, LoraModels, and Prompts.

A User can:
- Create a Diffusion Job by selecting a DiffusionModel, LoraModel, and Prompt.
- Create an Enhancement Job by slecting a Prompt.

- When a job is created, a task is enqueued to Django-RQ.
- The worker processes the job:
  - For Diffusion Jobs, it uses the selected DiffusionModel and LoraModel to generate images based on the Prompt.
  - For Enhancement Jobs, it enhances the Prompt using the selected enhancement method.
- The job status is updated in the DiffusionJobs model.
- Once the job is complete, results (images or enhanced prompts) are stored and linked to the job record.
- Users can view the status and results of their jobs in the admin interface.

