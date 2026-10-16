# Contributing

## Setting up your development environment

1. clone the repository:
    ```sh
    git clone <Repository urlL>
    ```
2. Continue with [Working on a task](#working-on-a-task-anchor)

## Keeping up-to-date

* Commit your changes very frequently. You do this with `git add .` and `git commit -m "<message>"` (or just `git commit -am "<message>"`). The message is a short description of what you did since you last commited.
Commiting often makes reviewing code a lot faster, since each commit is small and you do not have to dig through 500 lines of changes.
* Remember to run `git pull` from time to time to ensure merge conflicts can be resolved early. (Which makes resolving them a LOT easier)
* Push your changes on a somewhat frequent basis (`git push`). This helps others stay informed on the progress and can surface issues early instead of wasting precious time working on something defective.

## Your duties

* If you are asked to review a pull request, review it! Failing to do so will accumulate the feeling of "Uhh, what is this?", "Uhh, what does this do?" and "I have no idea what is going on".
Read through the pull request carefully, ask the author for clarification if you do not understand something.
* Merging a pull request should only be done by the author.

## Working on a task
<a name="working-on-a-task-anchor"></a>

1. Read through your assigned issue.
2. Mak sure that the issue is assigned to you.
3. Scroll down in your issue until you see the "development" section in the sidebar. Click "Create a branch" to create a branch for your issue. This will link the branch to your issue and automatically close the issue, once your branch gets merged into main.
4. Check out your newly created branch locally. You can now start developing. Remember following the steps in [Your duties](#your-duties)
5. Once you are done, create a pull request and have it reviewed.