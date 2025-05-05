#!/usr/bin/env python
import os
import sys
import csv
import argparse
import logging
from mysql.connector import connect as mysql_connect
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("test_data_preparation.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("test_data_preparation")

def load_config():
    """Load database configuration from environment variables."""
    load_dotenv()
    return {
        # MySQL configuration
        "MYSQL_HOST": os.getenv("CLOUD_DB_HOST", "localhost"),
        "MYSQL_USER": os.getenv("CLOUD_DB_USER", "root"),
        "MYSQL_PASSWORD": os.getenv("CLOUD_DB_PASSWORD", ""),
        "MYSQL_DB": os.getenv("CLOUD_DB_NAME", "career_db"),
    }

class TestDataExtractor:
    """Class for extracting test data from MySQL database."""
    
    def __init__(self, config):
        """Initialize with database configuration."""
        self.config = config
        self.conn = None
    
    def connect(self):
        """Connect to MySQL database."""
        try:
            self.conn = mysql_connect(
                host=self.config["MYSQL_HOST"],
                user=self.config["MYSQL_USER"],
                password=self.config["MYSQL_PASSWORD"],
                database=self.config["MYSQL_DB"],
                charset='utf8mb4'
            )
            logger.info("Connected to MySQL database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {str(e)}")
            return False
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("MySQL connection closed")
    
    def get_selection_process_info(self, selection_id):
        """Get information about a specific selection process."""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor(dictionary=True)
            query = """
            SELECT 
                id, 
                title,
                ankets,
                created
            FROM career_job_data 
            WHERE id = %s
            """
            cursor.execute(query, (selection_id,))
            selection_info = cursor.fetchone()
            cursor.close()
            
            if selection_info:
                logger.info(f"Found selection process {selection_id}: {selection_info['title']} with {selection_info['ankets']} applicants")
            else:
                logger.error(f"Selection process {selection_id} not found")
                
            return selection_info
        except Exception as e:
            logger.error(f"Error getting selection process info: {str(e)}")
            raise
    
    def extract_candidates_for_selection(self, selection_id):
        """Extract candidates who applied for a specific selection process.
        
        Args:
            selection_id: ID of the selection process
            
        Returns:
            List of candidate dictionaries with application details
        """
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor(dictionary=True)
            query = """
            SELECT 
                cad.id AS application_id,
                cad.job_id AS selection_id,
                cad.user_id AS candidate_id,
                cad.decide_id,
                cad.sub_decide,
                cud.firstname,
                cud.lastname,
                cud.email
            FROM 
                career_apply_data cad
            JOIN 
                career_user_data cud ON cad.user_id = cud.id
            WHERE 
                cad.job_id = %s
            ORDER BY 
                cad.id
            """
            cursor.execute(query, (selection_id,))
            candidates = cursor.fetchall()
            cursor.close()
            
            logger.info(f"Extracted {len(candidates)} candidates for selection process {selection_id}")
            return candidates
        except Exception as e:
            logger.error(f"Error extracting candidates: {str(e)}")
            raise
    
    def get_decision_labels(self):
        """Get decision labels for decide_id and sub_decide values."""
        try:
            if not self.conn:
                self.connect()
            
            # Get main decision labels
            cursor = self.conn.cursor(dictionary=True)
            query = """
            SELECT option_id, title 
            FROM career_site_data 
            WHERE grp_id = 5
            """
            cursor.execute(query)
            main_decisions = {row['option_id']: row['title'] for row in cursor.fetchall()}
            
            # Get sub-decision labels
            query = """
            SELECT option_id, title, parent_id 
            FROM career_site_data 
            WHERE grp_id = 6
            """
            cursor.execute(query)
            sub_decisions = {}
            for row in cursor.fetchall():
                if row['parent_id'] not in sub_decisions:
                    sub_decisions[row['parent_id']] = {}
                sub_decisions[row['parent_id']][row['option_id']] = row['title']
            
            cursor.close()
            
            logger.info(f"Retrieved decision labels: {len(main_decisions)} main decisions, {sum(len(v) for v in sub_decisions.values())} sub-decisions")
            return main_decisions, sub_decisions
        except Exception as e:
            logger.error(f"Error getting decision labels: {str(e)}")
            raise

def save_to_csv(candidates, selection_info, decision_labels, output_file):
    """Save extracted candidates data to CSV file.
    
    Args:
        candidates: List of candidate dictionaries
        selection_info: Dictionary containing selection process information
        decision_labels: Tuple of (main_decisions, sub_decisions) dictionaries
        output_file: Path to output CSV file
    """
    main_decisions, sub_decisions = decision_labels
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'application_id', 
                'selection_id', 
                'selection_title',
                'candidate_id', 
                'candidate_name',
                'email',
                'decide_id', 
                'decide_label',
                'sub_decide', 
                'sub_decide_label',
                'final_decision'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for candidate in candidates:
                # Get decision labels
                decide_label = main_decisions.get(candidate['decide_id'], 'Unknown')
                
                sub_decide_label = ''
                if candidate['decide_id'] in sub_decisions and candidate['sub_decide'] in sub_decisions[candidate['decide_id']]:
                    sub_decide_label = sub_decisions[candidate['decide_id']][candidate['sub_decide']]
                
                # Create readable final decision
                final_decision = decide_label
                if sub_decide_label:
                    final_decision = f"{decide_label} - {sub_decide_label}"
                    
                # Check if this is the "hired" candidate
                is_hired = (candidate['decide_id'] == 2 and candidate['sub_decide'] == 2)
                if is_hired:
                    final_decision = "Ажилд авсан"
                
                row = {
                    'application_id': candidate['application_id'],
                    'selection_id': candidate['selection_id'],
                    'selection_title': selection_info['title'],
                    'candidate_id': candidate['candidate_id'],
                    'candidate_name': f"{candidate['firstname']} {candidate['lastname']}",
                    'email': candidate['email'],
                    'decide_id': candidate['decide_id'],
                    'decide_label': decide_label,
                    'sub_decide': candidate['sub_decide'],
                    'sub_decide_label': sub_decide_label,
                    'final_decision': final_decision
                }
                
                writer.writerow(row)
        
        logger.info(f"Test data saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving to CSV: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Extract test data for a specific selection process')
    parser.add_argument('selection_id', type=int, help='ID of the selection process')
    parser.add_argument('--output', '-o', type=str, default=None, help='Output CSV file path')
    
    args = parser.parse_args()
    selection_id = args.selection_id
    
    # Set default output filename if not specified
    output_file = args.output
    if not output_file:
        output_file = f"selection_process_{selection_id}_test_data.csv"
    
    try:
        # Load configuration
        config = load_config()
        
        # Create extractor
        extractor = TestDataExtractor(config)
        
        # Get selection process info
        selection_info = extractor.get_selection_process_info(selection_id)
        if not selection_info:
            logger.error(f"Selection process {selection_id} not found. Exiting.")
            return False
        
        # Extract candidates who applied for this selection process
        candidates = extractor.extract_candidates_for_selection(selection_id)
        if not candidates:
            logger.warning(f"No candidates found for selection process {selection_id}")
            return False
        
        # Get decision labels
        decision_labels = extractor.get_decision_labels()
        
        # Save to CSV
        save_to_csv(candidates, selection_info, decision_labels, output_file)
        
        logger.info(f"Test data preparation completed for selection process {selection_id}")
        logger.info(f"Total candidates: {len(candidates)}")
        
        # Close database connection
        extractor.close()
        
        print(f"Test data preparation completed! Output saved to {output_file}")
        return True
    
    except Exception as e:
        logger.error(f"Error preparing test data: {str(e)}")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)