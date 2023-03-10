## Usage

### Enable the extension

1. Open Renderdoc. Goto 【Tools】- 【Manage Extensions】

   ![image-20230204104639790](_readme_/image-20230204104639790.png)

   

2. Click 【Open Location】. This would lead you to the plug-in folder that renderdoc reads.

   ![image-20230204104830077](_readme_/image-20230204104830077.png)

   

3. Open a terminal in that plug-in folder. Clone the repo with `--recurse-submodules` parameter.

   ```bash
   > git clone --recurse-submodules ssh://git@git-internal.nie.netease.com:32200/gzlixiaoliang/unrealdoc.git
   ```

   

4. Reopen the Extension Manager by step 1 && 2. You will see a new extension is added.

   ![image-20230204105502296](_readme_/image-20230204105502296.png)

   

5. Click 【Load】 and check 【Always Load】.  You can see the 【Unreal Toolbox】shows.

   ![image-20230204105631387](_readme_/image-20230204105631387.png)

   

### Scene Data Tool



### Pass Analysis Tool



### Mesh Draw Call Analysis Tool





## Write Your Own Tool

### Develop Environment and Debugging



### Main Workflow of a Tool

#### User Interface



#### Render Resource Data Acquisition

