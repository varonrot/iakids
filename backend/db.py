from supabase import create_client
import os

supabase = create_client(
    os.environ["https://bxnfzuglfwytiyaguwjj.supabase.co"],
    os.environ["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4bmZ6dWdsZnd5dGl5YWd1d2pqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTIyOTQ2NSwiZXhwIjoyMDg0ODA1NDY1fQ.L4bAwrk9nFVe2r60yUvOAJiucOL9ttTxFicsjmhW-44"]
)
