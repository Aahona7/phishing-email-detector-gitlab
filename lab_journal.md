MODULE 1:



Q1.1): What is the difference between the working

tree, the staging area (index), and a commit? What does --cached show that plain

git diff does not?



Working Tree:

Files on disk that I am editing.



Staging Area:

Temporary area where I select files before commit.



Commit:

Permanent snapshot stored in Git.



git diff:

Shows unstaged changes.



git diff --cached:

Shows staged changes.



Q1.2)What is the purpose of the staging area if you could just commit

everything at once? Describe one real project scenario where selective staging like this

would matter.



The hash is the SHA identifier of the commit object stored inside .git/objects.



The staging area allows committing related changes separately.



Real example:

While developing the phishing detector, I may fix a bug in email parsing and update README at the same time. I can commit them separately to keep history clean.



Q1.3) why would git commit --amend be

dangerous if you had already pushed this commit to a shared remote branch?



git commit --amend changes commit history.



If the commit was already pushed, rewriting history causes conflicts for collaborators because the old commit hash no longer exists.



Q1.4)What is stored inside a commit object? (List all fields you see in

the -p output.) - What does HEAD point to right now? - If you add a file and stage it but don’t

commit — does an object get created in .git/objects/? Test it and write what you find.



16/  19/  2a/  2b/  2d/  3f/  50/  c8/  e6/  f2/  fb/  info/  pack/

master

yes (16/  19/  2a/  2b/  2d/  3f/  50/  \*66/\*  c8/  e6/  f2/  fb/  info/  pack/)



MODULE 2:



Q2.1)



$ git log --oneline --all --graph

\* 2335079 (feature/url-analyser) improve url analysis module

\* 5fa6361 Add url analysis module

| \* a17e0be (feature/email-parser) Add email parser improvement

|/

\* 0fc44c2 (HEAD -> master) Add phishing email detector project files

\* 2ae8c07 Improve email detection logic and update journal

\* 2bc72d1 Add project doc and lab journal



Q2.2.1)will this be a fast-forward merge or a true merge commit? Write your prediction before running the command.



Prediction:

Fast-forward merge.



Reason:

master has not moved ahead after creating feature/email-parser.

Git can simply move master forward to the latest commit on that branch.

Result: Prediction was correct.



Reason:

master had not moved after creating feature/email-parser.

Git simply moved the master pointer to the latest commit on the branch instead of creating a new merge commit.



Q2.2.2) fast-forward or merge commit this time? Why is it different from the first merge?



Prediction:

This will create a merge commit.



Reason:

master already contains changes from feature/email-parser, and feature/url-analyser diverged from an earlier commit.



Result:

\*   1f8935a (HEAD -> master) Merge branch 'feature/url-analyser'

|\\

| \* 2335079 (feature/url-analyser) improve url analysis module

| \* 5fa6361 Add url analysis module

\* | a17e0be (feature/email-parser) Add email parser improvement

|/

\* 0fc44c2 Add phishing email detector project files

\* 2ae8c07 Improve email detection logic and update journal

\* 2bc72d1 Add project doc and lab journal



Prediction was correct.



Reason:

master and feature/url-analyser had diverged histories.

Git could not fast-forward because master already contained commits from another branch.



Fast-forward happens when the current branch has no new commits after branching.



A merge commit happens when both branches have separate histories.



The flag to force a merge commit is:



git merge --no-ff <branch>



This is useful when we want to preserve branch history even if fast-forward is possible.



Q2.3) If you had 5 files with conflicts, how would you know which ones still need resolution before you’re allowed to commit?



<<<<<<< HEAD

&#x20;   <title>SentryMail // Advanced Phishing Email Detector-prod</title>

=======

&#x20;   <title>SentryMail // Advanced Phishing Email Detector-Beta</title>

>>>>>>> fix/title



<<<<<<< HEAD

Current branch version.



=======

Separator between conflicting changes.



>>>>>>> fix/title

Incoming branch version.



To see unresolved conflicts:

git status



Files listed under:



both modified



still need conflict resolution.



Q2.4)What is the difference between git revert and git reset in this context? Write a 3-sentence explanation. 



git reset rewrites history by moving the branch pointer.



git revert does not rewrite history.

It creates a new commit that reverses previous changes.



git reset is safe only when commits have not been pushed.



git revert is safe even after pushing because it preserves commit history.



MODULE 3:



Q3.1) What does “origin” mean? Is it a fixed word or just a naming convention? - What will git push -u origin main do differently from git push origin main on subsequent pushes?



origin is not a special Git keyword.

It is simply the default name given to a remote repository.



git push -u origin master:

Pushes the branch and sets upstream tracking.



After upstream is set, future pushes can be done using:



git push



without specifying origin and master again.



Q3.2) what is the difference between git fetch and git pull? What does fetch do to your working directory? What does pull do? 



git fetch downloads changes from the remote repository.



It updates remote tracking branches like origin/master.



It does not change files in the working directory.



git pull performs fetch followed by merge.



git fetch:

Downloads commits but does not change files.



git pull:

Downloads commits and merges them into the current branch.



fetch is safer because I can inspect changes before merging.



Q3.3) What exactly is Git telling you? - Why did this happen? - What are the two ways to resolve this? (hint: merge pull vs rebase pull)



Git rejected the push because the remote repository contained commits that were not present in my local repository.



This happened because another clone pushed changes first.



Two ways to resolve this are:



1\. git pull (merge)

2\. git pull --rebase (rebase)



git pull:

Fetches and merges remote commits, creating a merge commit.



git pull --rebase:

Fetches remote commits and reapplies local commits on top of them.



Rebase creates a cleaner, linear history without extra merge commits.



Q3.4)What happens to your local branch when you do this? 



origin/feature/contact-page is the remote tracking branch.



It represents the version of feature/contact-page stored on GitHub.



Git uses this information for push, pull, and fetch operations.



Deleting a remote branch does not delete the local branch.



The local branch remains until it is deleted explicitly.





MODULE 4:



Q4.1)What checks would you want on a real PR before merging? Name at 

least 3 (think: code review, automated tests, branch up-to-date, no conflicts, etc.). Why 

might merging your own PR immediately defeat the purpose?



Checks before merging a PR:



1\. Code review by another developer

2\. Automated tests pass successfully

3\. Branch is up-to-date with master



Self-merging immediately defeats the purpose because

changes are not independently reviewed and bugs may go unnoticed.



Q4.2): git log main..feature/about-page — what does the .. syntax mean? 

What would git log feature/about-page..main show instead?



master..feature/about-page



Shows commits present in feature/about-page but absent in master.



feature/about-page..master



Shows commits present in master but absent in feature/about-page.



MODULE 5:



Q5.1)what exactly does cherry-pick do? Is it the same commit, or a new one? 



git cherry-pick copies the changes introduced by a commit

and creates a NEW commit on the current branch.



The commit hashes are different because Git creates

new commit objects with different parent histories,

even though the content is the same.



Q5.3)What command resumes a cherry-pick after resolving a conflict? 

What command aborts it entirely and restores the pre-cherry-pick state? How is this 

similar to resolving a merge conflict? 



git cherry-pick copies a specific commit from another branch.



If conflicts occur:

1\. Edit the conflicted file.

2\. Remove conflict markers.

3\. Stage the resolved file.

4\. Run:



git cherry-pick --continue



To cancel:



git cherry-pick --abort



MODULE 6:



Q6.1)What is the difference between git stash pop and git stash apply? When 

would you choose one over the other? What happens to a stash after pop vs apply? 



git stash temporarily saves uncommitted changes and removes them from the working directory.



It is useful when I want to switch branches or pull updates without committing unfinished work.



Command used:

git stash push -m "WIP phishing improvements"



After stashing, the working tree becomes clean while the changes are safely stored in the stash list.



Q6.2)How long does the reflog keep entries? What would you do if reflog also 

didn’t have the commit (i.e., older than the expiry)? What does this teach you about when 

“hard reset” is truly irreversible? 



git stash apply restores the stashed changes to the working directory but keeps the stash entry.



git stash pop restores the stashed changes and removes the stash entry from the stash list.



Commands used:



git stash apply

git stash pop



Difference:

apply = restore + keep stash

pop = restore + delete stash



Q6.3)you must describe what each column or piece of information in the output represents.



git stash temporarily stores uncommitted changes.



git stash apply:

Restores the stash but keeps it in the stash list.



git stash pop:

Restores the stash and removes it from the stash list.



git stash drop:

Deletes a stash entry.



