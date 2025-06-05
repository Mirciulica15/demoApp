#!/usr/bin/env python3
"""
GitHub Issue Importer for Bug Tickets
=====================================

This script imports bug tickets from a JSON file into a GitHub repository as issues.
It uses the GitHub API to create issues with proper labels, formatting, and metadata.

Requirements:
- PyGithub library (pip install PyGithub)
- GitHub personal access token with repo permissions
- Target repository with write access

Usage:
    python github_issue_importer.py --repo owner/repo-name --token your-token
    python github_issue_importer.py --repo owner/repo-name --token your-token --dry-run
    python github_issue_importer.py --config config.json
"""

import json
import argparse
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

try:
    from github import Github, Repository
    from github.GithubException import GithubException
except ImportError:
    print("Error: PyGithub library not found. Install it with: pip install PyGithub")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('github_issue_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GitHubIssueImporter:
    """Import bug tickets from JSON to GitHub issues."""
    
    def __init__(self, github_token: str, repository_name: str, dry_run: bool = False):
        """
        Initialize the importer.
        
        Args:
            github_token: GitHub personal access token
            repository_name: Repository in format 'owner/repo'
            dry_run: If True, only simulate without creating actual issues
        """
        self.github_token = github_token
        self.repository_name = repository_name
        self.dry_run = dry_run
        self.github_client = None
        self.repository = None
        
    def connect_to_github(self) -> bool:
        """Connect to GitHub API and get repository."""
        try:
            self.github_client = Github(self.github_token)
            
            # Test authentication
            user = self.github_client.get_user()
            logger.info(f"Connected to GitHub as: {user.login}")
            
            # Get repository
            self.repository = self.github_client.get_repo(self.repository_name)
            logger.info(f"Connected to repository: {self.repository.full_name}")
            
            return True
            
        except GithubException as e:
            logger.error(f"GitHub API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def load_bug_tickets(self, json_file_path: str) -> Optional[Dict]:
        """Load bug tickets from JSON file."""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                logger.info(f"Loaded {len(data.get('bugs', []))} bug tickets from {json_file_path}")
                return data
        except FileNotFoundError:
            logger.error(f"Bug tickets file not found: {json_file_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in bug tickets file: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading bug tickets: {e}")
            return None
    
    def format_issue_body(self, bug: Dict) -> str:
        """Format bug ticket data into GitHub issue body."""
        body_parts = [
            f"## Bug Description",
            f"{bug['description']}",
            "",
            f"## Details",
            f"- **Bug ID:** `{bug['id']}`",
            f"- **Severity:** {bug['severity'].title()}",
            f"- **Priority:** {bug['priority'].title()}",
            f"- **Type:** {bug['type'].title()}",
            f"- **File:** `{bug['file']}`",
            f"- **Line:** {bug.get('line_number', 'N/A')}",
            "",
            f"## Steps to Reproduce",
        ]
        
        for i, step in enumerate(bug.get('steps_to_reproduce', []), 1):
            body_parts.append(f"{i}. {step}")
        
        body_parts.extend([
            "",
            f"## Expected Behavior",
            f"{bug['expected_behavior']}",
            "",
            f"## Actual Behavior", 
            f"{bug['actual_behavior']}",
            "",
            f"---",
            f"*Auto-imported from bug ticket system on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])
        
        return "\n".join(body_parts)
    
    def get_severity_priority_labels(self, bug: Dict) -> List[str]:
        """Generate severity and priority labels."""
        labels = []
        
        # Add severity label with emoji
        severity = bug.get('severity', 'medium').lower()
        severity_labels = {
            'critical': '🔥 critical',
            'high': '🚨 high severity',
            'medium': '⚠️ medium severity', 
            'low': '📝 low severity'
        }
        labels.append(severity_labels.get(severity, '⚠️ medium severity'))
        
        # Add priority label
        priority = bug.get('priority', 'medium').lower()
        priority_labels = {
            'critical': '🎯 urgent',
            'high': '📈 high priority',
            'medium': '📊 medium priority',
            'low': '📉 low priority'
        }
        labels.append(priority_labels.get(priority, '📊 medium priority'))
        
        return labels
    
    def create_github_issue(self, bug: Dict) -> Optional[str]:
        """Create a GitHub issue from bug ticket."""
        try:
            # Prepare issue data
            title = f"[{bug['id']}] {bug['title']}"
            body = self.format_issue_body(bug)
            
            # Prepare labels
            labels = self.get_severity_priority_labels(bug)
            labels.extend(bug.get('labels', []))
            
            if self.dry_run:
                logger.info(f"DRY RUN - Would create issue: {title}")
                logger.info(f"  Labels: {', '.join(labels)}")
                return f"dry-run-{bug['id']}"
            
            # Create the issue
            issue = self.repository.create_issue(
                title=title,
                body=body,
                labels=labels
            )
            
            logger.info(f"Created issue #{issue.number}: {title}")
            return str(issue.number)
            
        except GithubException as e:
            logger.error(f"Failed to create issue for {bug['id']}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating issue for {bug['id']}: {e}")
            return None
    
    def import_all_bugs(self, json_file_path: str) -> Dict[str, str]:
        """Import all bugs from JSON file to GitHub issues."""
        # Load bug data
        bug_data = self.load_bug_tickets(json_file_path)
        if not bug_data:
            return {}
        
        # Connect to GitHub
        if not self.connect_to_github():
            return {}
        
        # Import each bug
        results = {}
        bugs = bug_data.get('bugs', [])
        
        logger.info(f"Starting import of {len(bugs)} bugs...")
        
        for i, bug in enumerate(bugs, 1):
            logger.info(f"Processing bug {i}/{len(bugs)}: {bug['id']}")
            
            issue_number = self.create_github_issue(bug)
            if issue_number:
                results[bug['id']] = issue_number
            
            # Small delay to avoid rate limiting
            if not self.dry_run and i < len(bugs):
                import time
                time.sleep(1)
        
        logger.info(f"Import completed. Successfully imported {len(results)} out of {len(bugs)} bugs.")
        return results
    
    def create_labels_if_needed(self) -> bool:
        """Create common labels in the repository if they don't exist."""
        try:
            if self.dry_run:
                logger.info("DRY RUN - Would create/check labels")
                return True
            
            # Define standard labels for bug tracking
            standard_labels = [
                {'name': '🔥 critical', 'color': 'B60205', 'description': 'Critical severity bugs'},
                {'name': '🚨 high severity', 'color': 'D93F0B', 'description': 'High severity bugs'},
                {'name': '⚠️ medium severity', 'color': 'FBCA04', 'description': 'Medium severity bugs'},
                {'name': '📝 low severity', 'color': '0E8A16', 'description': 'Low severity bugs'},
                {'name': '🎯 urgent', 'color': 'B60205', 'description': 'Urgent priority'},
                {'name': '📈 high priority', 'color': 'D93F0B', 'description': 'High priority'},
                {'name': '📊 medium priority', 'color': 'FBCA04', 'description': 'Medium priority'},
                {'name': '📉 low priority', 'color': '0E8A16', 'description': 'Low priority'},
                {'name': 'bug', 'color': 'D73A49', 'description': 'Something is not working'},
                {'name': 'ui', 'color': '1D76DB', 'description': 'User interface related'},
                {'name': 'accessibility', 'color': '7057FF', 'description': 'Accessibility improvements'},
                {'name': 'security', 'color': 'B60205', 'description': 'Security vulnerability'},
            ]
            
            existing_labels = {label.name for label in self.repository.get_labels()}
            
            for label_info in standard_labels:
                if label_info['name'] not in existing_labels:
                    try:
                        self.repository.create_label(
                            name=label_info['name'],
                            color=label_info['color'],
                            description=label_info['description']
                        )
                        logger.info(f"Created label: {label_info['name']}")
                    except GithubException as e:
                        logger.warning(f"Could not create label {label_info['name']}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating labels: {e}")
            return False

def load_config(config_file: str) -> Dict:
    """Load configuration from JSON file."""
    try:
        with open(config_file, 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Error loading config file: {e}")
        return {}

def main():
    """Main function to handle command line arguments and run the importer."""
    parser = argparse.ArgumentParser(
        description="Import bug tickets from JSON to GitHub issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python github_issue_importer.py --repo myuser/myrepo --token ghp_xxxx
  python github_issue_importer.py --repo myuser/myrepo --token ghp_xxxx --dry-run
  python github_issue_importer.py --config config.json --bugs-file custom_bugs.json
        """
    )
    
    parser.add_argument('--repo', help='GitHub repository in format owner/repo')
    parser.add_argument('--token', help='GitHub personal access token')
    parser.add_argument('--bugs-file', default='bug_tickets.json', 
                       help='Path to bug tickets JSON file (default: bug_tickets.json)')
    parser.add_argument('--config', help='Path to configuration JSON file')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Simulate import without creating actual issues')
    parser.add_argument('--create-labels', action='store_true',
                       help='Create standard labels in repository')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config:
        config = load_config(args.config)
    
    # Get repository and token
    repository = args.repo or config.get('repository')
    token = args.token or config.get('github_token') or os.getenv('GITHUB_TOKEN')
    bugs_file = args.bugs_file or config.get('bugs_file', 'bug_tickets.json')
    
    if not repository:
        logger.error("Repository not specified. Use --repo or config file.")
        sys.exit(1)
        
    if not token:
        logger.error("GitHub token not specified. Use --token, config file, or GITHUB_TOKEN env var.")
        sys.exit(1)
    
    # Initialize importer
    importer = GitHubIssueImporter(token, repository, args.dry_run)
    
    # Create labels if requested
    if args.create_labels:
        logger.info("Creating standard labels...")
        if not importer.connect_to_github():
            sys.exit(1)
        importer.create_labels_if_needed()
    
    # Import bugs
    results = importer.import_all_bugs(bugs_file)
    
    if results:
        logger.info(f"Successfully imported {len(results)} issues:")
        for bug_id, issue_number in results.items():
            logger.info(f"  {bug_id} -> Issue #{issue_number}")
        
        # Save results
        results_file = f"import_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as file:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'repository': repository,
                'imported_count': len(results),
                'results': results
            }, file, indent=2)
        logger.info(f"Results saved to: {results_file}")
    else:
        logger.error("No issues were imported successfully.")
        sys.exit(1)

if __name__ == "__main__":
    main()
