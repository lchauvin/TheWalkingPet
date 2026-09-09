# Deployment secrets

Files here are mounted into the production stack as Docker secrets and are
never baked into an image.

- `firebase-credentials.json` — Firebase service account key
  (Firebase Console → Project Settings → Service Accounts → Generate new private key).

Everything in this directory except this README is gitignored. Nothing here
should ever be committed.
