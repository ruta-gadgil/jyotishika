"""
Test to verify that analysis notes are preserved when profile is updated.

This test verifies the fix for the issue where notes were deleted when
chart-affecting fields (datetime, latitude, longitude, house_system, 
ayanamsha, node_type) were updated.

With the fix, the chart is updated in place instead of being deleted,
which preserves the chart_id and prevents notes from being cascade-deleted.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Profile, Chart, AnalysisNote
from datetime import datetime
import uuid

def test_profile_update_preserves_notes():
    """
    Test that updating chart-affecting fields preserves analysis notes.
    
    Steps:
    1. Create a user and profile
    2. Create a chart for the profile
    3. Add analysis notes to the chart
    4. Update chart-affecting fields (e.g., latitude, ayanamsha)
    5. Verify that:
       - Chart still exists (not deleted)
       - Chart ID is the same (updated in place)
       - Analysis notes still exist
       - Chart data has been updated
    """
    app = create_app()
    
    with app.app_context():
        # Clean up test data if exists
        test_email = f"test_notes_{uuid.uuid4().hex[:8]}@example.com"
        
        try:
            # Step 1: Create test user
            user = User(
                email=test_email,
                name="Test User",
                email_verified=True
            )
            db.session.add(user)
            db.session.commit()
            print(f"✅ Created test user: {user.id}")
            
            # Step 2: Create test profile
            profile = Profile(
                user_id=user.id,
                name="Test Profile",
                datetime="1990-01-01T12:00:00",
                tz="America/New_York",
                utc_offset_minutes=-300,
                latitude=40.7128,
                longitude=-74.0060,
                house_system="PLACIDUS",
                ayanamsha="LAHIRI",
                node_type="TRUE_NODE"
            )
            db.session.add(profile)
            db.session.commit()
            print(f"✅ Created test profile: {profile.id}")
            
            # Step 3: Create a chart for the profile
            from app.chart_calc import calculate_chart_for_profile
            from app.db import save_chart
            
            chart_data = calculate_chart_for_profile(profile)
            chart = save_chart(profile.id, chart_data)
            original_chart_id = chart.id
            print(f"✅ Created chart: {chart.id}")
            
            # Step 4: Add analysis notes
            note1 = AnalysisNote(
                chart_id=chart.id,
                title="Test Note 1",
                note="This is a test note about the chart."
            )
            note2 = AnalysisNote(
                chart_id=chart.id,
                title="Test Note 2",
                note="Another test note with observations."
            )
            db.session.add(note1)
            db.session.add(note2)
            db.session.commit()
            note1_id = note1.id
            note2_id = note2.id
            print(f"✅ Created 2 analysis notes: {note1_id}, {note2_id}")
            
            # Step 5: Update chart-affecting fields
            from app.db import update_profile
            
            updates = {
                'latitude': 41.0,  # Change latitude
                'ayanamsha': 'RAMAN'  # Change ayanamsha
            }
            
            updated_profile, error = update_profile(profile.id, user.id, updates)
            
            if error:
                print(f"❌ Profile update failed: {error}")
                return False
            
            print(f"✅ Updated profile with chart-affecting fields")
            
            # Step 6: Verify results
            # Refresh objects from DB
            db.session.expire_all()
            
            # Check chart still exists
            chart_after = Chart.query.filter_by(profile_id=profile.id).first()
            if not chart_after:
                print("❌ FAIL: Chart was deleted (should have been updated in place)")
                return False
            
            print(f"✅ Chart still exists: {chart_after.id}")
            
            # Check chart ID is the same
            if chart_after.id != original_chart_id:
                print(f"❌ FAIL: Chart ID changed from {original_chart_id} to {chart_after.id}")
                return False
            
            print(f"✅ Chart ID preserved: {chart_after.id}")
            
            # Check notes still exist
            notes_after = AnalysisNote.query.filter_by(chart_id=chart_after.id).all()
            if len(notes_after) != 2:
                print(f"❌ FAIL: Expected 2 notes, found {len(notes_after)}")
                return False
            
            print(f"✅ Both notes preserved: {len(notes_after)} notes found")
            
            # Check chart data was updated
            if chart_after.chart_metadata.get('ayanamsha') != 'RAMAN':
                print(f"❌ FAIL: Chart ayanamsha not updated: {chart_after.chart_metadata.get('ayanamsha')}")
                return False
            
            print(f"✅ Chart data updated (ayanamsha: {chart_after.chart_metadata.get('ayanamsha')})")
            
            # Verify latitude update in profile
            profile_after = Profile.query.get(profile.id)
            if profile_after.latitude != 41.0:
                print(f"❌ FAIL: Profile latitude not updated: {profile_after.latitude}")
                return False
            
            print(f"✅ Profile updated (latitude: {profile_after.latitude})")
            
            print("\n🎉 TEST PASSED: Profile update preserves analysis notes!")
            return True
            
        finally:
            # Cleanup
            try:
                if user:
                    # Delete user (cascades to profile, chart, notes)
                    db.session.delete(user)
                    db.session.commit()
                    print(f"\n🧹 Cleaned up test data")
            except Exception as e:
                print(f"\n⚠️  Cleanup error: {e}")
                db.session.rollback()


if __name__ == "__main__":
    success = test_profile_update_preserves_notes()
    sys.exit(0 if success else 1)
