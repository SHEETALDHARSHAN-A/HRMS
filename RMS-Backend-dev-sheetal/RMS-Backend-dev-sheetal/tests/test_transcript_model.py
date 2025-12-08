def test_transcript_model_import_and_tablename():
    # Import the model and assert basic attributes exist
    from app.db.models.transcript_model import Transcript

    assert hasattr(Transcript, "__tablename__")
    assert Transcript.__tablename__ == "transcripts"
    # Ensure Column-backed attributes are present on the class
    assert hasattr(Transcript, "conversation")
    assert hasattr(Transcript, "profile_id")
    assert hasattr(Transcript, "job_id")
